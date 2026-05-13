"""Tests for AudioData Pydantic model and load_audio function.

All audio is generated synthetically in-memory -- no WAV files in repo.
"""

from pathlib import Path

import numpy as np
import pytest

from phantom.audio import AudioData, load_audio
from phantom.exceptions import AudioLoadError, PathSecurityError


# ── AudioData model tests ──────────────────────────────────────────────


class TestAudioDataMono:
    """Tests for AudioData with mono audio."""

    def test_mono_metadata(self, mono_sine_440hz):
        """AudioData with mono samples stores correct metadata."""
        samples, sr = mono_sine_440hz
        samples_2d = samples.reshape(-1, 1)
        ad = AudioData(
            samples=samples_2d,
            sample_rate=sr,
            num_channels=1,
            duration=len(samples) / sr,
            num_samples=len(samples),
        )
        assert ad.sample_rate == sr
        assert ad.num_channels == 1
        assert ad.duration == pytest.approx(1.0, abs=1e-4)
        assert ad.num_samples == sr

    def test_mono_left(self, mono_sine_440hz):
        """AudioData.left returns samples[:, 0] for mono."""
        samples, sr = mono_sine_440hz
        samples_2d = samples.reshape(-1, 1)
        ad = AudioData(
            samples=samples_2d,
            sample_rate=sr,
            num_channels=1,
            duration=len(samples) / sr,
            num_samples=len(samples),
        )
        np.testing.assert_array_equal(ad.left, samples)

    def test_mono_right_raises(self, mono_sine_440hz):
        """AudioData.right raises AudioLoadError for mono files."""
        samples, sr = mono_sine_440hz
        samples_2d = samples.reshape(-1, 1)
        ad = AudioData(
            samples=samples_2d,
            sample_rate=sr,
            num_channels=1,
            duration=len(samples) / sr,
            num_samples=len(samples),
        )
        with pytest.raises(AudioLoadError, match="mono"):
            _ = ad.right

    def test_mono_mono_property(self, mono_sine_440hz):
        """AudioData.mono returns samples[:, 0] for mono input."""
        samples, sr = mono_sine_440hz
        samples_2d = samples.reshape(-1, 1)
        ad = AudioData(
            samples=samples_2d,
            sample_rate=sr,
            num_channels=1,
            duration=len(samples) / sr,
            num_samples=len(samples),
        )
        np.testing.assert_array_equal(ad.mono, samples)


class TestAudioDataStereo:
    """Tests for AudioData with stereo audio."""

    def test_stereo_metadata(self, stereo_sine_440hz):
        """AudioData with stereo samples stores correct metadata."""
        samples, sr = stereo_sine_440hz
        ad = AudioData(
            samples=samples,
            sample_rate=sr,
            num_channels=2,
            duration=len(samples) / sr,
            num_samples=len(samples),
        )
        assert ad.sample_rate == sr
        assert ad.num_channels == 2
        assert ad.duration == pytest.approx(1.0, abs=1e-4)
        assert ad.num_samples == sr

    def test_stereo_left(self, stereo_sine_440hz):
        """AudioData.left returns samples[:, 0] for stereo."""
        samples, sr = stereo_sine_440hz
        ad = AudioData(
            samples=samples,
            sample_rate=sr,
            num_channels=2,
            duration=len(samples) / sr,
            num_samples=len(samples),
        )
        np.testing.assert_array_equal(ad.left, samples[:, 0])

    def test_stereo_right(self, stereo_sine_440hz):
        """AudioData.right returns samples[:, 1] for stereo."""
        samples, sr = stereo_sine_440hz
        ad = AudioData(
            samples=samples,
            sample_rate=sr,
            num_channels=2,
            duration=len(samples) / sr,
            num_samples=len(samples),
        )
        np.testing.assert_array_equal(ad.right, samples[:, 1])

    def test_stereo_mono_is_mean(self, stereo_sine_440hz):
        """AudioData.mono returns mean of L and R for stereo (within float tolerance)."""
        samples, sr = stereo_sine_440hz
        ad = AudioData(
            samples=samples,
            sample_rate=sr,
            num_channels=2,
            duration=len(samples) / sr,
            num_samples=len(samples),
        )
        expected = np.mean(samples[:, :2], axis=1)
        np.testing.assert_allclose(ad.mono, expected, atol=1e-7)


class TestAudioDataValidation:
    """Tests for AudioData model validation."""

    def test_rejects_1d_samples(self):
        """AudioData rejects samples with ndim != 2."""
        samples_1d = np.zeros(100, dtype=np.float32)
        with pytest.raises(ValueError):
            AudioData(
                samples=samples_1d,
                sample_rate=44100,
                num_channels=1,
                duration=100 / 44100,
                num_samples=100,
            )

    def test_rejects_channel_mismatch(self):
        """AudioData rejects samples where shape[1] != num_channels."""
        samples = np.zeros((100, 2), dtype=np.float32)
        with pytest.raises(ValueError):
            AudioData(
                samples=samples,
                sample_rate=44100,
                num_channels=1,  # mismatch: 2 columns but num_channels=1
                duration=100 / 44100,
                num_samples=100,
            )

    def test_file_path_defaults_none(self, mono_sine_440hz):
        """AudioData.file_path defaults to None."""
        samples, sr = mono_sine_440hz
        samples_2d = samples.reshape(-1, 1)
        ad = AudioData(
            samples=samples_2d,
            sample_rate=sr,
            num_channels=1,
            duration=len(samples) / sr,
            num_samples=len(samples),
        )
        assert ad.file_path is None


# ── load_audio function tests ──────────────────────────────────────────


class TestLoadAudio:
    """Tests for the load_audio function."""

    def test_load_mono_wav(self, wav_file_factory, mono_sine_440hz):
        """load_audio loads a mono WAV and returns AudioData with correct metadata."""
        samples, sr = mono_sine_440hz
        path = wav_file_factory(samples, sr)
        result = load_audio(path)
        assert isinstance(result, AudioData)
        assert result.num_channels == 1
        assert result.sample_rate == sr
        assert result.num_samples == len(samples)
        assert result.duration == pytest.approx(len(samples) / sr, abs=1e-4)
        assert result.file_path == path

    def test_load_stereo_wav(self, wav_file_factory, stereo_sine_440hz):
        """load_audio loads a stereo WAV and returns AudioData with correct metadata."""
        samples, sr = stereo_sine_440hz
        path = wav_file_factory(samples, sr)
        result = load_audio(path)
        assert isinstance(result, AudioData)
        assert result.num_channels == 2
        assert result.sample_rate == sr
        assert result.num_samples == len(samples)

    def test_rejects_multichannel(self, multichannel_wav):
        """load_audio rejects a 3+ channel file with AudioLoadError."""
        with pytest.raises(AudioLoadError, match="mono and stereo"):
            load_audio(multichannel_wav)

    def test_nonexistent_file_raises(self):
        """load_audio raises AudioLoadError for nonexistent file."""
        with pytest.raises(AudioLoadError, match="Cannot read"):
            load_audio("/nonexistent/path/audio.wav")

    def test_returns_float32(self, wav_file_factory, mono_sine_440hz):
        """load_audio returns float32 samples normalized to [-1.0, 1.0]."""
        samples, sr = mono_sine_440hz
        path = wav_file_factory(samples, sr)
        result = load_audio(path)
        assert result.samples.dtype == np.float32
        assert result.samples.max() <= 1.0
        assert result.samples.min() >= -1.0


# ── Edge case tests (D-13) ─────────────────────────────────────────────


class TestEdgeCases:
    """Edge case tests: short audio, high sample rate, near-silence."""

    @pytest.mark.parametrize(
        "duration,sr,amplitude",
        [
            (0.1, 44100, 1.0),  # Short audio <0.2s
            (1.0, 96000, 1.0),  # High sample rate
            (1.0, 44100, 1e-5),  # Near-silence ~-100dBFS
        ],
        ids=["short-audio", "high-sample-rate", "near-silence"],
    )
    def test_edge_cases(self, wav_file_factory, duration, sr, amplitude):
        """load_audio handles edge-case audio without error."""
        num_samples = int(duration * sr)
        t = np.linspace(0, duration, num_samples, endpoint=False, dtype=np.float32)
        samples = (amplitude * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        path = wav_file_factory(samples, sr)
        result = load_audio(path)
        assert isinstance(result, AudioData)
        assert result.sample_rate == sr
        assert result.num_samples == num_samples


# ── Multi-format tests ────────────────────────────────────────────────


class TestMultiFormat:
    """Tests for FLAC, AIFF, and OGG format support."""

    @pytest.mark.parametrize("fmt", ["FLAC", "AIFF", "OGG"])
    def test_load_format(self, audio_file_factory, mono_sine_440hz, fmt):
        """load_audio reads FLAC, AIFF, and OGG files."""
        samples, sr = mono_sine_440hz
        path = audio_file_factory(samples, sr, fmt=fmt)
        result = load_audio(path)
        assert isinstance(result, AudioData)
        assert result.sample_rate == sr
        assert result.num_channels == 1
        assert result.num_samples == len(samples)

    @pytest.mark.parametrize("fmt", ["FLAC", "AIFF", "OGG"])
    def test_stereo_format(self, audio_file_factory, stereo_sine_440hz, fmt):
        """Stereo FLAC/AIFF/OGG loads correctly."""
        samples, sr = stereo_sine_440hz
        path = audio_file_factory(samples, sr, fmt=fmt)
        result = load_audio(path)
        assert result.num_channels == 2
        assert result.num_samples == len(samples)

    @pytest.mark.parametrize("fmt", ["FLAC", "AIFF"])
    def test_samples_match_wav(self, audio_file_factory, mono_sine_440hz, fmt):
        """Same source signal produces equivalent AudioData across formats."""
        samples, sr = mono_sine_440hz
        wav_path = audio_file_factory(samples, sr, fmt="WAV")
        other_path = audio_file_factory(samples, sr, fmt=fmt)
        wav_result = load_audio(wav_path)
        other_result = load_audio(other_path)
        np.testing.assert_allclose(wav_result.samples, other_result.samples, atol=1e-4)


# ── Security guard tests (Phase 10.2) ────────────────────────────────


class TestLoadAudioSecurityGuards:
    """Tests for load_audio() path validation and duration/size guards."""

    # -- Path validation integration (SEC-01) --

    def test_path_validation_rejects_outside_dir(
        self, tmp_path, monkeypatch, wav_file_factory, mono_sine_440hz
    ):
        """load_audio rejects paths outside PHANTOM_AUDIO_DIR."""
        allowed = tmp_path / "allowed"
        allowed.mkdir()
        monkeypatch.setenv("PHANTOM_AUDIO_DIR", str(allowed))
        samples, sr = mono_sine_440hz
        path = wav_file_factory(samples, sr)  # created in tmp_path, NOT in allowed
        with pytest.raises(PathSecurityError, match="outside the allowed directory"):
            load_audio(path)

    def test_path_validation_unrestricted_without_env(
        self, monkeypatch, wav_file_factory, mono_sine_440hz
    ):
        """load_audio works normally when PHANTOM_AUDIO_DIR is unset (D-13)."""
        monkeypatch.delenv("PHANTOM_AUDIO_DIR", raising=False)
        monkeypatch.delenv("PHANTOM_MAX_DURATION", raising=False)
        monkeypatch.delenv("PHANTOM_MAX_FILE_SIZE", raising=False)
        samples, sr = mono_sine_440hz
        path = wav_file_factory(samples, sr)
        result = load_audio(path)
        assert result.sample_rate == sr

    # -- Duration guard (SEC-03, D-05, D-06, D-07) --

    def test_duration_exceeding_param_rejected(self, wav_file_factory):
        """load_audio rejects files exceeding max_duration parameter."""
        # Create a 2-second WAV, set limit to 1 second
        samples = np.zeros((88200, 1), dtype=np.float32)  # 2s at 44100
        path = wav_file_factory(samples, 44100)
        with pytest.raises(AudioLoadError, match="exceeds the"):
            load_audio(path, max_duration=1.0)

    def test_duration_within_param_accepted(self, wav_file_factory, mono_sine_440hz):
        """load_audio accepts files within max_duration parameter."""
        samples, sr = mono_sine_440hz
        path = wav_file_factory(samples, sr)
        result = load_audio(path, max_duration=60.0)
        assert isinstance(result, AudioData)

    def test_duration_env_overrides_default(self, wav_file_factory, monkeypatch):
        """PHANTOM_MAX_DURATION env var overrides the 900s default."""
        monkeypatch.setenv("PHANTOM_MAX_DURATION", "1")
        samples = np.zeros((88200, 1), dtype=np.float32)  # 2s
        path = wav_file_factory(samples, 44100)
        with pytest.raises(AudioLoadError, match="exceeds the"):
            load_audio(path)

    def test_duration_param_overrides_env(self, wav_file_factory, monkeypatch):
        """max_duration parameter overrides PHANTOM_MAX_DURATION env var."""
        monkeypatch.setenv("PHANTOM_MAX_DURATION", "1")  # would reject 2s
        samples = np.zeros((88200, 1), dtype=np.float32)  # 2s
        path = wav_file_factory(samples, 44100)
        result = load_audio(path, max_duration=60.0)  # param says 60s, overrides env
        assert isinstance(result, AudioData)

    def test_duration_error_message_format(self, wav_file_factory):
        """Duration error includes actual duration, limit, and remediation (D-07)."""
        samples = np.zeros((88200, 1), dtype=np.float32)  # 2s
        path = wav_file_factory(samples, 44100)
        with pytest.raises(AudioLoadError, match=r"PHANTOM_MAX_DURATION"):
            load_audio(path, max_duration=1.0)

    # -- File size guard (D-08) --

    def test_file_size_exceeding_param_rejected(self, wav_file_factory):
        """load_audio rejects files exceeding max_file_size parameter."""
        samples = np.zeros((44100, 1), dtype=np.float32)  # ~176KB WAV
        path = wav_file_factory(samples, 44100)
        with pytest.raises(AudioLoadError, match="exceeds the"):
            load_audio(path, max_file_size=100)  # 100 bytes limit

    def test_file_size_within_param_accepted(self, wav_file_factory, mono_sine_440hz):
        """load_audio accepts files within max_file_size parameter."""
        samples, sr = mono_sine_440hz
        path = wav_file_factory(samples, sr)
        result = load_audio(path, max_file_size=500_000_000)
        assert isinstance(result, AudioData)

    def test_file_size_env_overrides_default(self, wav_file_factory, monkeypatch):
        """PHANTOM_MAX_FILE_SIZE env var overrides the 500MB default."""
        monkeypatch.setenv("PHANTOM_MAX_FILE_SIZE", "100")  # 100 bytes
        samples = np.zeros((44100, 1), dtype=np.float32)
        path = wav_file_factory(samples, 44100)
        with pytest.raises(AudioLoadError, match="exceeds the"):
            load_audio(path)

    def test_file_size_param_overrides_env(self, wav_file_factory, monkeypatch):
        """max_file_size parameter overrides PHANTOM_MAX_FILE_SIZE env var."""
        monkeypatch.setenv("PHANTOM_MAX_FILE_SIZE", "100")  # would reject
        samples = np.zeros((44100, 1), dtype=np.float32)
        path = wav_file_factory(samples, 44100)
        result = load_audio(path, max_file_size=500_000_000)  # param overrides
        assert isinstance(result, AudioData)

    def test_file_size_error_message_format(self, wav_file_factory):
        """File size error includes actual size and limit."""
        samples = np.zeros((44100, 1), dtype=np.float32)
        path = wav_file_factory(samples, 44100)
        with pytest.raises(AudioLoadError, match=r"PHANTOM_MAX_FILE_SIZE"):
            load_audio(path, max_file_size=100)


# ── Input validation edge case tests (Phase 11.1, SC 6-10) ──────────


class TestInputValidationEdgeCases:
    """Tests for negative/zero guards, sample rate range, and malformed env vars."""

    # -- Negative/zero max_duration (SC-6) --

    def test_negative_max_duration_rejected(self, wav_file_factory, mono_sine_440hz):
        """load_audio rejects negative max_duration with 'positive' in error."""
        samples, sr = mono_sine_440hz
        path = wav_file_factory(samples, sr)
        with pytest.raises(AudioLoadError, match="positive"):
            load_audio(path, max_duration=-5.0)

    def test_zero_max_duration_rejected(self, wav_file_factory, mono_sine_440hz):
        """load_audio rejects zero max_duration with 'positive' in error."""
        samples, sr = mono_sine_440hz
        path = wav_file_factory(samples, sr)
        with pytest.raises(AudioLoadError, match="positive"):
            load_audio(path, max_duration=0.0)

    def test_negative_max_file_size_rejected(self, wav_file_factory, mono_sine_440hz):
        """load_audio rejects negative max_file_size with 'positive' in error."""
        samples, sr = mono_sine_440hz
        path = wav_file_factory(samples, sr)
        with pytest.raises(AudioLoadError, match="positive"):
            load_audio(path, max_file_size=-100)

    def test_zero_max_file_size_rejected(self, wav_file_factory, mono_sine_440hz):
        """load_audio rejects zero max_file_size with 'positive' in error."""
        samples, sr = mono_sine_440hz
        path = wav_file_factory(samples, sr)
        with pytest.raises(AudioLoadError, match="positive"):
            load_audio(path, max_file_size=0)

    # -- Malformed env vars (SC-10) --

    def test_env_max_duration_zero_rejected(
        self, wav_file_factory, mono_sine_440hz, monkeypatch
    ):
        """PHANTOM_MAX_DURATION='0' raises AudioLoadError matching 'positive'."""
        monkeypatch.setenv("PHANTOM_MAX_DURATION", "0")
        samples, sr = mono_sine_440hz
        path = wav_file_factory(samples, sr)
        with pytest.raises(AudioLoadError, match="positive"):
            load_audio(path)

    def test_env_max_duration_negative_rejected(
        self, wav_file_factory, mono_sine_440hz, monkeypatch
    ):
        """PHANTOM_MAX_DURATION='-1' raises AudioLoadError matching 'positive'."""
        monkeypatch.setenv("PHANTOM_MAX_DURATION", "-1")
        samples, sr = mono_sine_440hz
        path = wav_file_factory(samples, sr)
        with pytest.raises(AudioLoadError, match="positive"):
            load_audio(path)

    def test_env_max_duration_empty_uses_default(
        self, wav_file_factory, mono_sine_440hz, monkeypatch
    ):
        """PHANTOM_MAX_DURATION='' is treated as unset, uses 900s default."""
        monkeypatch.setenv("PHANTOM_MAX_DURATION", "")
        samples, sr = mono_sine_440hz
        path = wav_file_factory(samples, sr)
        # Should not raise -- empty string treated as unset, default 900s
        result = load_audio(path)
        assert result.sample_rate == sr

    def test_env_max_file_size_zero_rejected(
        self, wav_file_factory, mono_sine_440hz, monkeypatch
    ):
        """PHANTOM_MAX_FILE_SIZE='0' raises AudioLoadError matching 'positive'."""
        monkeypatch.setenv("PHANTOM_MAX_FILE_SIZE", "0")
        samples, sr = mono_sine_440hz
        path = wav_file_factory(samples, sr)
        with pytest.raises(AudioLoadError, match="positive"):
            load_audio(path)

    def test_env_max_file_size_negative_rejected(
        self, wav_file_factory, mono_sine_440hz, monkeypatch
    ):
        """PHANTOM_MAX_FILE_SIZE='-1' raises AudioLoadError matching 'positive'."""
        monkeypatch.setenv("PHANTOM_MAX_FILE_SIZE", "-1")
        samples, sr = mono_sine_440hz
        path = wav_file_factory(samples, sr)
        with pytest.raises(AudioLoadError, match="positive"):
            load_audio(path)

    def test_env_max_file_size_empty_uses_default(
        self, wav_file_factory, mono_sine_440hz, monkeypatch
    ):
        """PHANTOM_MAX_FILE_SIZE='' is treated as unset, uses 500MB default."""
        monkeypatch.setenv("PHANTOM_MAX_FILE_SIZE", "")
        samples, sr = mono_sine_440hz
        path = wav_file_factory(samples, sr)
        result = load_audio(path)
        assert result.sample_rate == sr

    def test_env_max_file_size_abc_rejected(
        self, wav_file_factory, mono_sine_440hz, monkeypatch
    ):
        """PHANTOM_MAX_FILE_SIZE='abc' raises AudioLoadError matching 'integer'."""
        monkeypatch.setenv("PHANTOM_MAX_FILE_SIZE", "abc")
        samples, sr = mono_sine_440hz
        path = wav_file_factory(samples, sr)
        with pytest.raises(AudioLoadError, match="integer"):
            load_audio(path)

    # -- Sample rate range validation (SC-9) --

    def test_low_sample_rate_rejected(self, tmp_path):
        """WAV with 4000 Hz sample rate is rejected."""
        import soundfile as sf

        sr = 4000
        samples = np.zeros((sr, 1), dtype=np.float32)  # 1 second
        path = str(tmp_path / "low_sr.wav")
        sf.write(path, samples, sr)
        with pytest.raises(AudioLoadError, match="supported range"):
            load_audio(path)

    def test_high_sample_rate_rejected(self, tmp_path):
        """WAV with 500000 Hz sample rate is rejected."""
        import soundfile as sf

        sr = 500000
        samples = np.zeros((sr, 1), dtype=np.float32)
        path = str(tmp_path / "high_sr.wav")
        sf.write(path, samples, sr)
        with pytest.raises(AudioLoadError, match="supported range"):
            load_audio(path)

    def test_boundary_8000_hz_accepted(self, tmp_path):
        """WAV with 8000 Hz sample rate is accepted (boundary)."""
        import soundfile as sf

        sr = 8000
        samples = np.zeros((sr, 1), dtype=np.float32)
        path = str(tmp_path / "boundary_8k.wav")
        sf.write(path, samples, sr)
        result = load_audio(path)
        assert result.sample_rate == 8000

    def test_boundary_384000_hz_accepted(self, tmp_path):
        """WAV with 384000 Hz sample rate is accepted (boundary)."""
        import soundfile as sf

        sr = 384000
        samples = np.zeros((sr, 1), dtype=np.float32)
        path = str(tmp_path / "boundary_384k.wav")
        sf.write(path, samples, sr)
        result = load_audio(path)
        assert result.sample_rate == 384000


# ── Unsupported format detection tests ────────────────────────────────


class TestUnsupportedFormats:
    """Tests for clear error messages when loading unsupported audio formats."""

    def test_mp3_raises_with_format_name(self, tmp_path):
        """load_audio('track.mp3') raises AudioLoadError with 'MP3' in message."""
        path = str(tmp_path / "track.mp3")
        Path(path).touch()
        with pytest.raises(AudioLoadError, match="MP3"):
            load_audio(path)

    def test_aac_raises_with_format_name(self, tmp_path):
        """load_audio('track.aac') raises AudioLoadError with 'AAC' in message."""
        path = str(tmp_path / "track.aac")
        Path(path).touch()
        with pytest.raises(AudioLoadError, match="AAC"):
            load_audio(path)

    def test_m4a_raises_with_format_name(self, tmp_path):
        """load_audio('track.m4a') raises AudioLoadError with 'M4A' in message."""
        path = str(tmp_path / "track.m4a")
        Path(path).touch()
        with pytest.raises(AudioLoadError, match="M4A"):
            load_audio(path)

    def test_wma_raises_with_format_name(self, tmp_path):
        """load_audio('track.wma') raises AudioLoadError with 'WMA' in message."""
        path = str(tmp_path / "track.wma")
        Path(path).touch()
        with pytest.raises(AudioLoadError, match="WMA"):
            load_audio(path)

    def test_nonexistent_wav_still_raises_generic(self):
        """load_audio for a nonexistent .wav still raises AudioLoadError with generic message."""
        with pytest.raises(AudioLoadError, match="Cannot read"):
            load_audio("/nonexistent/path/audio.wav")

    def test_error_includes_render_command(self, tmp_path):
        """Error message includes 'phantom render track.mp3 --format wav'."""
        path = str(tmp_path / "track.mp3")
        Path(path).touch()
        with pytest.raises(AudioLoadError, match=r"phantom render track\.mp3 --format wav"):
            load_audio(path)
