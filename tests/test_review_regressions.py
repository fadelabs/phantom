"""Behavioral regressions found during the September project review."""

import os

import numpy as np
import pytest
import soundfile as sf

from phantom._settings import AnalysisSettings
from phantom.audio import AudioData, load_audio
from phantom.exceptions import AnalysisError, AudioLoadError
from phantom.loudness import analyze_loudness
from phantom.problems import detect_problems


def stereo_audio(right_sign=1):
    sr = 44100
    tone = (0.5 * np.sin(2 * np.pi * 440 * np.arange(sr) / sr)).astype(np.float32)
    return AudioData(
        samples=np.column_stack([tone, right_sign * tone]),
        sample_rate=sr,
        num_channels=2,
        num_samples=sr,
        duration=1,
    )


def test_loudness_is_invariant_to_channel_polarity():
    normal = analyze_loudness(stereo_audio())
    inverted = analyze_loudness(stereo_audio(-1))
    assert inverted.integrated_lufs == normal.integrated_lufs
    assert inverted.true_peak_dbtp == normal.true_peak_dbtp
    assert inverted.integrated_lufs is not None


@pytest.mark.parametrize("subtype", ["PCM_16", "PCM_24", "FLOAT"])
def test_positive_clipping_survives_stereo_downmix(tmp_path, subtype):
    audio = stereo_audio()
    audio.samples[100:200, 0] = 1.0
    audio.samples[:, 1] = 0
    path = tmp_path / "clipped.wav"
    sf.write(path, audio.samples, audio.sample_rate, subtype=subtype)
    result = detect_problems(load_audio(str(path)))
    clipping = next(p for p in result.problems if p.type == "clipping")
    assert clipping.details.clipped_samples == 100


def test_antiphase_dc_does_not_short_circuit_problem_detection():
    audio = stereo_audio(-1)
    audio.samples[:, 0] += 0.1
    audio.samples[:, 1] -= 0.1
    result = detect_problems(audio)
    assert any(p.type == "dc_offset" for p in result.problems)


@pytest.mark.parametrize(
    "values",
    [
        {"spectral_hop_size": 0},
        {"spectrum_frame_size": 1},
        {"flatness_frame_size": -2},
        {"clipping_threshold": float("nan")},
    ],
)
def test_invalid_settings_fail_before_native_analysis(values):
    with pytest.raises(AnalysisError):
        AnalysisSettings(**values)


@pytest.mark.timeout(3)
def test_fifo_audio_is_rejected_without_blocking(tmp_path):
    path = tmp_path / "pipe.wav"
    os.mkfifo(path)
    with pytest.raises(AudioLoadError):
        load_audio(str(path))


@pytest.mark.parametrize(
    "payload", [b'{"x": NaN}', b'{"x": Infinity}', b"\xff", b" " * 1000001]
)
def test_metrics_rejects_unsafe_payloads(tmp_path, monkeypatch, payload):
    from phantom.live_metrics import read_live_metrics

    monkeypatch.setenv("PHANTOM_METRICS_DIR", str(tmp_path))
    (tmp_path / "instance.json").write_bytes(payload)
    with pytest.raises(AnalysisError):
        read_live_metrics()


def test_aggregate_guard_resolves_paths_against_input_root(tmp_path, monkeypatch):
    from fastmcp.exceptions import ToolError

    from phantom.server import _validate_batch_inputs

    path = tmp_path / "test.wav"
    sf.write(path, stereo_audio().samples, 44100)
    monkeypatch.setenv("PHANTOM_AUDIO_DIR", str(tmp_path))
    monkeypatch.setenv("PHANTOM_MAX_AGGREGATE_BYTES", "100")
    with pytest.raises(ToolError, match="aggregate limit"):
        _validate_batch_inputs(["test.wav"])


def test_processing_preserves_float_headroom_and_separate_sandboxes(
    tmp_path, monkeypatch
):
    pytest.importorskip("pedalboard")
    from phantom.processing import apply_processing, fix_audio

    source = tmp_path / "input"
    source.mkdir()
    dest = tmp_path / "output"
    dest.mkdir()
    monkeypatch.setenv("PHANTOM_AUDIO_DIR", str(source))
    monkeypatch.setenv("PHANTOM_OUTPUT_DIR", str(dest))
    samples = stereo_audio().samples * 3
    sf.write(source / "source.wav", samples, 44100, subtype="FLOAT")
    result = fix_audio("source.wav", problems=[], output_path="fixed.wav")
    output, _ = sf.read(result.output_path, dtype="float32", always_2d=True)
    np.testing.assert_array_equal(output, samples)
    assert any(p.type == "clipping" for p in result.after.problems)
    result = apply_processing("source.wav", [], "custom.wav")
    output, _ = sf.read(result.output_path, dtype="float32", always_2d=True)
    np.testing.assert_array_equal(output, samples)


def test_missing_native_engine_keeps_doctor_and_cli_available(monkeypatch):
    from click.testing import CliRunner

    from phantom import _essentia
    from phantom.cli import cli

    def unavailable(_name):
        raise ImportError("native library missing")

    monkeypatch.setattr(_essentia, "import_module", unavailable)
    result = CliRunner().invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "doctor" in result.output
    with pytest.raises(AnalysisError, match="Run phantom doctor"):
        _essentia.LoudnessEBUR128()


def test_resampling_checks_budget_before_allocating(monkeypatch):
    from phantom import _resample

    monkeypatch.setenv("PHANTOM_MAX_DECODED_BYTES", "1000")

    def unexpected_allocation(*_args, **_kwargs):
        pytest.fail("Native resampling must not run over the configured budget")

    monkeypatch.setattr(_resample, "resample_poly", unexpected_allocation)
    with pytest.raises(AudioLoadError, match="decoded"):
        _resample.resample_to_match(stereo_audio(), 96000)
