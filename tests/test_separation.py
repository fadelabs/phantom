"""Tests for the source separation module.

Covers SEP-01 through SEP-03.
All tests mock Demucs since it is an optional heavyweight dependency.
"""

import importlib
import os

import numpy as np
import pytest
from unittest.mock import patch, MagicMock

from phantom.separation import separate_stems, SeparationResult
from phantom.exceptions import (
    AnalysisError,
    AudioLoadError,
    DependencyMissingError,
    PathSecurityError,
)


def _make_demucs_mocks(samplerate=44100):
    """Create mocks for demucs.pretrained, demucs.apply, demucs.audio, torch."""
    mock_model = MagicMock()
    mock_model.samplerate = samplerate
    mock_model.audio_channels = 2
    mock_model.sources = ["drums", "bass", "other", "vocals"]

    mock_pretrained = MagicMock()
    mock_pretrained.get_model.return_value = mock_model

    mock_apply_module = MagicMock()
    # apply_model returns shape [batch, sources, channels, samples]
    stem_tensor = MagicMock()
    stem_audio = np.zeros((2, samplerate), dtype=np.float32)
    stem_tensor.cpu.return_value.numpy.return_value.T = stem_audio.T
    sources = MagicMock()
    sources.__getitem__ = lambda self, i: stem_tensor
    sources.shape = (1, 4, 2, samplerate)
    batch_sources = MagicMock()
    batch_sources.__getitem__ = lambda self, i: sources
    mock_apply_module.apply_model.return_value = batch_sources

    wav_data = MagicMock()
    wav_data.mean.return_value = MagicMock(
        mean=MagicMock(return_value=0.0),
        std=MagicMock(return_value=1.0),
    )
    mock_audio_file_cls = MagicMock(
        return_value=MagicMock(
            read=MagicMock(return_value=wav_data),
        )
    )
    mock_audio_module = MagicMock()
    mock_audio_module.AudioFile = mock_audio_file_cls

    mock_torch = MagicMock()
    mock_torch.no_grad.return_value.__enter__ = MagicMock(return_value=None)
    mock_torch.no_grad.return_value.__exit__ = MagicMock(return_value=False)

    mock_sf = MagicMock()

    return {
        "demucs": MagicMock(),
        "demucs.pretrained": mock_pretrained,
        "demucs.apply": mock_apply_module,
        "demucs.audio": mock_audio_module,
        "torch": mock_torch,
        "soundfile": mock_sf,
        "_model": mock_model,
        "_pretrained": mock_pretrained,
        "_apply": mock_apply_module,
        "_sf": mock_sf,
    }


class TestSeparateStems:
    """Tests for Demucs-based source separation (SEP-01 through SEP-03)."""

    def test_missing_demucs_raises_dependency_error(self, monkeypatch):
        """When demucs is not installed, DependencyMissingError is raised (SEP-03)."""
        import builtins
        import sys

        for mod in ["demucs", "demucs.pretrained", "demucs.apply", "demucs.audio"]:
            monkeypatch.delitem(sys.modules, mod, raising=False)

        original_import = builtins.__import__

        def _mock_import(name, *args, **kwargs):
            if name.startswith("demucs"):
                raise ImportError(f"No module named '{name}'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", _mock_import)

        with pytest.raises(DependencyMissingError) as exc_info:
            separate_stems("any.wav", "/tmp/out")
        assert "pip install phantom[separation]" in str(exc_info.value)

    def test_missing_input_raises_file_not_found(self, tmp_path):
        """AudioLoadError when input_path does not exist (SEP-01)."""
        nonexistent = str(tmp_path / "nonexistent.wav")
        output_dir = str(tmp_path / "stems")
        mocks = _make_demucs_mocks()
        with patch.dict(
            "sys.modules",
            {
                "demucs.pretrained": mocks["demucs.pretrained"],
                "demucs.apply": mocks["demucs.apply"],
                "demucs.audio": mocks["demucs.audio"],
                "demucs": mocks["demucs"],
                "torch": mocks["torch"],
            },
        ):
            with pytest.raises(AudioLoadError, match="Input file not found"):
                separate_stems(nonexistent, output_dir)

    def test_successful_separation(self, tmp_path, wav_file_factory):
        """Successful separation returns dict mapping stem names to file paths (SEP-01)."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
        samples = np.column_stack(
            [
                0.5 * np.sin(2 * np.pi * 440 * t),
                0.5 * np.sin(2 * np.pi * 440 * t),
            ]
        ).astype(np.float32)
        input_path = wav_file_factory(samples, sr)
        output_dir = str(tmp_path / "stems")

        mocks = _make_demucs_mocks()
        with patch.dict(
            "sys.modules",
            {
                "demucs.pretrained": mocks["demucs.pretrained"],
                "demucs.apply": mocks["demucs.apply"],
                "demucs.audio": mocks["demucs.audio"],
                "demucs": mocks["demucs"],
                "torch": mocks["torch"],
            },
        ):
            result = separate_stems(input_path, output_dir)

        assert isinstance(result, SeparationResult)
        assert set(result.stems.keys()) == {"vocals", "drums", "bass", "other"}
        for stem_name, stem_path in result.stems.items():
            assert stem_path.endswith(f"{stem_name}.wav")

    def test_model_is_htdemucs(self, tmp_path, wav_file_factory):
        """get_model is called with 'htdemucs' (D-03)."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
        samples = np.column_stack(
            [
                0.5 * np.sin(2 * np.pi * 440 * t),
                0.5 * np.sin(2 * np.pi * 440 * t),
            ]
        ).astype(np.float32)
        input_path = wav_file_factory(samples, sr)
        output_dir = str(tmp_path / "stems")

        mocks = _make_demucs_mocks()
        with patch.dict(
            "sys.modules",
            {
                "demucs.pretrained": mocks["demucs.pretrained"],
                "demucs.apply": mocks["demucs.apply"],
                "demucs.audio": mocks["demucs.audio"],
                "demucs": mocks["demucs"],
                "torch": mocks["torch"],
            },
        ):
            separate_stems(input_path, output_dir)

        mocks["_pretrained"].get_model.assert_called_once_with("htdemucs")

    def test_output_dir_created(self, tmp_path, wav_file_factory):
        """Output directory is created if it does not exist."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
        samples = np.column_stack(
            [
                0.5 * np.sin(2 * np.pi * 440 * t),
                0.5 * np.sin(2 * np.pi * 440 * t),
            ]
        ).astype(np.float32)
        input_path = wav_file_factory(samples, sr)
        output_dir = str(tmp_path / "deeply" / "nested" / "stems")

        assert not os.path.isdir(output_dir)

        mocks = _make_demucs_mocks()
        with patch.dict(
            "sys.modules",
            {
                "demucs.pretrained": mocks["demucs.pretrained"],
                "demucs.apply": mocks["demucs.apply"],
                "demucs.audio": mocks["demucs.audio"],
                "demucs": mocks["demucs"],
                "torch": mocks["torch"],
            },
        ):
            separate_stems(input_path, output_dir)

        assert os.path.isdir(output_dir)

    def test_demucs_error_wrapped_in_analysis_error(self, tmp_path, wav_file_factory):
        """Demucs internal error is wrapped in AnalysisError."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
        samples = np.column_stack(
            [
                0.5 * np.sin(2 * np.pi * 440 * t),
                0.5 * np.sin(2 * np.pi * 440 * t),
            ]
        ).astype(np.float32)
        input_path = wav_file_factory(samples, sr)
        output_dir = str(tmp_path / "stems")

        mocks = _make_demucs_mocks()
        mocks["_apply"].apply_model.side_effect = RuntimeError(
            "Internal demucs failure"
        )

        with patch.dict(
            "sys.modules",
            {
                "demucs.pretrained": mocks["demucs.pretrained"],
                "demucs.apply": mocks["demucs.apply"],
                "demucs.audio": mocks["demucs.audio"],
                "demucs": mocks["demucs"],
                "torch": mocks["torch"],
            },
        ):
            with pytest.raises(AnalysisError, match="Source separation failed"):
                separate_stems(input_path, output_dir)

    def test_function_signature(self, tmp_path):
        """separate_stems accepts exactly 2 positional args named input_path and output_dir (D-04)."""
        mocks = _make_demucs_mocks()
        with patch.dict(
            "sys.modules",
            {
                "demucs.pretrained": mocks["demucs.pretrained"],
                "demucs.apply": mocks["demucs.apply"],
                "demucs.audio": mocks["demucs.audio"],
                "demucs": mocks["demucs"],
                "torch": mocks["torch"],
            },
        ):
            with pytest.raises(AudioLoadError):
                separate_stems(
                    input_path=str(tmp_path / "a.wav"),
                    output_dir=str(tmp_path / "out"),
                )

    def test_import_without_demucs(self, monkeypatch):
        """Importing phantom.separation without demucs installed does not raise (SEP-02)."""
        import builtins
        import sys
        import phantom.separation

        for mod in ["demucs", "demucs.pretrained", "demucs.apply", "demucs.audio"]:
            monkeypatch.delitem(sys.modules, mod, raising=False)

        original_import = builtins.__import__

        def _mock_import(name, *args, **kwargs):
            if name.startswith("demucs"):
                raise ImportError(f"No module named '{name}'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", _mock_import)
        importlib.reload(phantom.separation)


class TestOutputDirValidation:
    """Tests for PHANTOM_OUTPUT_DIR validation in separate_stems()."""

    def test_output_dir_rejected_when_outside(self, tmp_path, monkeypatch):
        """separate_stems rejects output_dir outside PHANTOM_OUTPUT_DIR."""
        allowed = tmp_path / "allowed"
        allowed.mkdir()
        monkeypatch.setenv("PHANTOM_OUTPUT_DIR", str(allowed))
        input_file = tmp_path / "input.wav"
        input_file.write_bytes(b"fake")
        with pytest.raises(PathSecurityError, match="outside the allowed directory"):
            separate_stems(str(input_file), str(tmp_path / "forbidden"))

    def test_output_dir_unrestricted_without_env(self, monkeypatch):
        """separate_stems does not restrict output_dir when PHANTOM_OUTPUT_DIR unset (D-11)."""
        monkeypatch.delenv("PHANTOM_OUTPUT_DIR", raising=False)
        try:
            separate_stems("/nonexistent/input.wav", "/any/output/dir")
        except PathSecurityError:
            pytest.fail("PathSecurityError raised when PHANTOM_OUTPUT_DIR is unset")
        except Exception:
            pass
