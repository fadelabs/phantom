"""Tests for phantom._utils shared helpers."""

from __future__ import annotations

import os

import numpy as np
import pytest

from phantom._utils import (
    _block_rms_db,
    _get_env_float,
    _get_env_int,
    guarded_mono,
    open_validated_input,
    validate_input_path,
    validate_output_path,
    wrap_errors,
)
from phantom.exceptions import (
    AnalysisError,
    AudioLoadError,
    DependencyMissingError,
    PathSecurityError,
    ProfileLoadError,
)


class TestBlockRmsDb:
    """Tests for the _block_rms_db helper."""

    def test_all_zeros_returns_empty(self) -> None:
        """All-silent input produces an empty list (no non-silent blocks)."""
        mono = np.zeros(44100, dtype=np.float32)
        result = _block_rms_db(mono)
        assert result == []

    def test_known_amplitude_sine(self) -> None:
        """A 0.5-amplitude sine (~-6 dBFS) produces block values near -6 dB."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float64)
        mono = 0.5 * np.sin(2 * np.pi * 1000 * t)
        result = _block_rms_db(mono)
        assert len(result) > 0
        # RMS of a sine with amplitude A is A / sqrt(2),
        # so 0.5 / sqrt(2) ~ 0.3536 => 20*log10(0.3536) ~ -9.03 dBFS
        # But due to block boundaries, allow a tolerance range.
        expected_rms_db = 20.0 * np.log10(0.5 / np.sqrt(2))
        for val in result:
            assert abs(val - expected_rms_db) < 1.0, (
                f"Block RMS {val:.2f} dB not within 1 dB of expected {expected_rms_db:.2f}"
            )

    def test_custom_block_size_hop(self) -> None:
        """Custom block_size and hop produce more blocks than defaults."""
        sr = 44100
        mono = 0.5 * np.ones(sr, dtype=np.float64)  # constant amplitude
        default_result = _block_rms_db(mono)
        custom_result = _block_rms_db(mono, block_size=2048, hop=1024)
        assert len(custom_result) > len(default_result)

    def test_return_type_is_list_of_float(self) -> None:
        """Return value is a list of Python floats."""
        mono = np.ones(8192, dtype=np.float64)
        result = _block_rms_db(mono)
        assert isinstance(result, list)
        for val in result:
            assert isinstance(val, float)

    def test_block_count_matches_formula(self) -> None:
        """Number of blocks matches (len - block_size) // hop + 1 for non-silent signal."""
        mono = np.ones(44100, dtype=np.float64)  # all non-silent
        block_size = 4096
        hop = 2048
        expected_count = (len(mono) - block_size) // hop + 1
        result = _block_rms_db(mono, block_size=block_size, hop=hop)
        assert len(result) == expected_count


class TestGuardedMono:
    """Tests for the shared empty/silence guard (B.2)."""

    @staticmethod
    def _audio(samples_1d: np.ndarray, sr: int):
        from phantom.audio import AudioData

        return AudioData(
            samples=samples_1d.reshape(-1, 1),
            sample_rate=sr,
            num_channels=1,
            duration=len(samples_1d) / sr,
            num_samples=len(samples_1d),
        )

    def test_audible_returns_mono(self):
        """An audible signal returns the mono mixdown unchanged."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
        samples = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        audio = self._audio(samples, sr)

        mono = guarded_mono(audio, "Spectral analysis failed")
        assert mono is not None
        np.testing.assert_array_equal(mono, audio.mono)

    def test_near_silent_returns_none(self):
        """A near-silent signal returns None so the caller returns its empty
        result without running the analysis (D-12)."""
        sr = 44100
        # ~-100 dBFS: well below the -80 dBFS silence threshold
        samples = (np.ones(sr, dtype=np.float32) * 1e-5).astype(np.float32)
        audio = self._audio(samples, sr)

        assert audio.is_near_silent is True
        assert guarded_mono(audio, "Spectral analysis failed") is None

    def test_zero_samples_raises_with_label(self):
        """Zero samples raise AnalysisError carrying the caller's label."""
        from phantom.exceptions import AnalysisError

        audio = self._audio(np.zeros(0, dtype=np.float32), 44100)
        with pytest.raises(
            AnalysisError, match="Spectral analysis failed: audio has 0 samples"
        ):
            guarded_mono(audio, "Spectral analysis failed")

    def test_label_round_trips_verbatim(self):
        """The label is embedded exactly as passed, so per-module messages
        stay byte-identical to the pre-helper raise sites."""
        from phantom.exceptions import AnalysisError

        audio = self._audio(np.zeros(0, dtype=np.float32), 44100)
        with pytest.raises(
            AnalysisError, match="Masking analysis failed: audio has 0 samples"
        ):
            guarded_mono(audio, "Masking analysis failed")


class TestValidateInputPath:
    """Tests for validate_input_path() -- SEC-01 path containment."""

    def test_unrestricted_when_env_unset(self, monkeypatch) -> None:
        """Returns path unchanged when PHANTOM_AUDIO_DIR is not set (D-13)."""
        monkeypatch.delenv("PHANTOM_AUDIO_DIR", raising=False)
        result = validate_input_path("/any/path/file.wav")
        assert result == "/any/path/file.wav"

    def test_relative_resolved_against_audio_dir(self, tmp_path, monkeypatch) -> None:
        """Relative paths resolve against PHANTOM_AUDIO_DIR (D-01)."""
        monkeypatch.setenv("PHANTOM_AUDIO_DIR", str(tmp_path))
        wav = tmp_path / "drums.wav"
        wav.write_bytes(b"fake")
        result = validate_input_path("drums.wav")
        assert result == os.path.realpath(str(wav))

    def test_absolute_inside_accepted(self, tmp_path, monkeypatch) -> None:
        """Absolute path inside PHANTOM_AUDIO_DIR is accepted."""
        monkeypatch.setenv("PHANTOM_AUDIO_DIR", str(tmp_path))
        wav = tmp_path / "track.wav"
        wav.write_bytes(b"fake")
        result = validate_input_path(str(wav))
        assert result == os.path.realpath(str(wav))

    def test_absolute_outside_rejected(self, tmp_path, monkeypatch) -> None:
        """Absolute path outside PHANTOM_AUDIO_DIR raises PathSecurityError."""
        monkeypatch.setenv("PHANTOM_AUDIO_DIR", str(tmp_path / "allowed"))
        (tmp_path / "allowed").mkdir()
        with pytest.raises(PathSecurityError, match="outside the allowed directory"):
            validate_input_path(str(tmp_path / "forbidden" / "evil.wav"))

    def test_symlink_inside_accepted(self, tmp_path, monkeypatch) -> None:
        """Symlink pointing inside PHANTOM_AUDIO_DIR is accepted (D-02)."""
        monkeypatch.setenv("PHANTOM_AUDIO_DIR", str(tmp_path))
        real_file = tmp_path / "real.wav"
        real_file.write_bytes(b"fake")
        link = tmp_path / "link.wav"
        link.symlink_to(real_file)
        result = validate_input_path(str(link))
        assert result == os.path.realpath(str(real_file))

    def test_symlink_outside_rejected(self, tmp_path, monkeypatch) -> None:
        """Symlink pointing outside PHANTOM_AUDIO_DIR is rejected (D-02)."""
        allowed = tmp_path / "allowed"
        allowed.mkdir()
        monkeypatch.setenv("PHANTOM_AUDIO_DIR", str(allowed))
        outside_file = tmp_path / "outside.wav"
        outside_file.write_bytes(b"fake")
        link = allowed / "sneaky.wav"
        link.symlink_to(outside_file)
        with pytest.raises(PathSecurityError, match="outside the allowed directory"):
            validate_input_path(str(link))

    def test_traversal_rejected(self, tmp_path, monkeypatch) -> None:
        """Path traversal via ../ is rejected after realpath resolution."""
        allowed = tmp_path / "allowed"
        allowed.mkdir()
        monkeypatch.setenv("PHANTOM_AUDIO_DIR", str(allowed))
        with pytest.raises(PathSecurityError, match="outside the allowed directory"):
            validate_input_path(str(allowed / ".." / "etc" / "passwd"))

    def test_directory_prefix_collision(self, tmp_path, monkeypatch) -> None:
        """'/allowed' must not accept paths in '/allowed_other/' (os.sep check)."""
        allowed = tmp_path / "audio"
        allowed.mkdir()
        other = tmp_path / "audio_extra"
        other.mkdir()
        monkeypatch.setenv("PHANTOM_AUDIO_DIR", str(allowed))
        with pytest.raises(PathSecurityError, match="outside the allowed directory"):
            validate_input_path(str(other / "file.wav"))

    def test_nonexistent_audio_dir_rejected(self, tmp_path, monkeypatch) -> None:
        """PHANTOM_AUDIO_DIR pointing to nonexistent directory raises PathSecurityError."""
        nonexistent = str(tmp_path / "does_not_exist")
        monkeypatch.setenv("PHANTOM_AUDIO_DIR", nonexistent)
        with pytest.raises(PathSecurityError, match="does not exist"):
            validate_input_path(str(tmp_path / "does_not_exist" / "file.wav"))


class TestOpenValidatedInput:
    """Tests for open_validated_input() -- Finding 4 symlink TOCTOU hardening."""

    def test_regular_file_unconfined(self, tmp_path, monkeypatch):
        """A regular file opens and returns a usable fd when unconfined."""
        monkeypatch.delenv("PHANTOM_AUDIO_DIR", raising=False)
        f = tmp_path / "a.wav"
        f.write_bytes(b"data")
        fd = open_validated_input(str(f))
        try:
            assert os.read(fd, 4) == b"data"
        finally:
            os.close(fd)

    def test_symlink_followed_when_unconfined(self, tmp_path, monkeypatch):
        """When PHANTOM_AUDIO_DIR is unset, symlinks are followed (legacy behavior)."""
        monkeypatch.delenv("PHANTOM_AUDIO_DIR", raising=False)
        target = tmp_path / "real.wav"
        target.write_bytes(b"data")
        link = tmp_path / "link.wav"
        link.symlink_to(target)
        fd = open_validated_input(str(link))
        os.close(fd)  # no raise == followed

    def test_symlink_rejected_when_confined(self, tmp_path, monkeypatch):
        """With PHANTOM_AUDIO_DIR set, a final-component symlink is rejected (O_NOFOLLOW)."""
        monkeypatch.setenv("PHANTOM_AUDIO_DIR", str(tmp_path))
        target = tmp_path / "real.wav"
        target.write_bytes(b"data")
        link = tmp_path / "link.wav"
        link.symlink_to(target)
        with pytest.raises(AudioLoadError, match="Cannot read audio file"):
            open_validated_input(str(link))

    def test_non_regular_rejected(self, tmp_path, monkeypatch):
        """A directory (non-regular file) is rejected."""
        monkeypatch.delenv("PHANTOM_AUDIO_DIR", raising=False)
        with pytest.raises(AudioLoadError):
            open_validated_input(str(tmp_path))


class TestValidateOutputPath:
    """Tests for validate_output_path() -- SEC-02 output containment."""

    def test_default_sandbox_when_env_unset(self, tmp_path, monkeypatch) -> None:
        """Unset PHANTOM_OUTPUT_DIR confines writes to ~/.phantom/output (Finding 1)."""
        monkeypatch.delenv("PHANTOM_OUTPUT_DIR", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))
        result = validate_output_path("song.wav")
        sandbox = tmp_path / ".phantom" / "output"
        assert sandbox.is_dir()  # created on demand
        assert result == os.path.realpath(str(sandbox / "song.wav"))

    def test_outside_default_sandbox_rejected(self, tmp_path, monkeypatch) -> None:
        """Absolute path outside the default sandbox is rejected (Finding 1)."""
        monkeypatch.delenv("PHANTOM_OUTPUT_DIR", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))
        with pytest.raises(PathSecurityError, match="outside the allowed directory"):
            validate_output_path(str(tmp_path / "elsewhere" / "evil.wav"))

    def test_inside_accepted(self, tmp_path, monkeypatch) -> None:
        """Path inside PHANTOM_OUTPUT_DIR is accepted."""
        monkeypatch.setenv("PHANTOM_OUTPUT_DIR", str(tmp_path))
        out = tmp_path / "stems"
        out.mkdir()
        result = validate_output_path(str(out))
        assert result == os.path.realpath(str(out))

    def test_outside_rejected(self, tmp_path, monkeypatch) -> None:
        """Path outside PHANTOM_OUTPUT_DIR raises PathSecurityError."""
        allowed = tmp_path / "outputs"
        allowed.mkdir()
        monkeypatch.setenv("PHANTOM_OUTPUT_DIR", str(allowed))
        with pytest.raises(PathSecurityError, match="outside the allowed directory"):
            validate_output_path(str(tmp_path / "elsewhere"))

    def test_symlink_outside_rejected(self, tmp_path, monkeypatch) -> None:
        """Symlink pointing outside PHANTOM_OUTPUT_DIR is rejected."""
        allowed = tmp_path / "outputs"
        allowed.mkdir()
        monkeypatch.setenv("PHANTOM_OUTPUT_DIR", str(allowed))
        outside = tmp_path / "elsewhere"
        outside.mkdir()
        link = allowed / "sneaky"
        link.symlink_to(outside)
        with pytest.raises(PathSecurityError, match="outside the allowed directory"):
            validate_output_path(str(link))


class TestWrapErrors:
    """Tests for the wrap_errors decorator."""

    def test_normal_return_passes_through(self) -> None:
        """A decorated function that returns normally passes the value unchanged."""

        @wrap_errors("Test failed")
        def add(a: int, b: int) -> int:
            return a + b

        assert add(2, 3) == 5

    def test_analysis_error_passes_through(self) -> None:
        """AnalysisError raised inside the decorated function passes through unchanged."""

        @wrap_errors("Prefix")
        def fail() -> None:
            raise AnalysisError("original message")

        with pytest.raises(AnalysisError, match="original message"):
            fail()

    def test_audio_load_error_passes_through(self) -> None:
        """AudioLoadError (PhantomError subclass) passes through unchanged."""

        @wrap_errors("Prefix")
        def fail() -> None:
            raise AudioLoadError("cannot load file")

        with pytest.raises(AudioLoadError, match="cannot load file"):
            fail()

    def test_dependency_missing_error_passes_through(self) -> None:
        """DependencyMissingError (PhantomError subclass) passes through unchanged."""

        @wrap_errors("Prefix")
        def fail() -> None:
            raise DependencyMissingError("demucs", "separate")

        with pytest.raises(DependencyMissingError):
            fail()

    def test_path_security_error_passes_through(self) -> None:
        """PathSecurityError (PhantomError subclass) passes through unchanged."""

        @wrap_errors("Prefix")
        def fail() -> None:
            raise PathSecurityError("path outside allowed dir")

        with pytest.raises(PathSecurityError, match="path outside allowed dir"):
            fail()

    def test_profile_load_error_passes_through(self) -> None:
        """ProfileLoadError (PhantomError subclass) passes through unchanged."""

        @wrap_errors("Prefix")
        def fail() -> None:
            raise ProfileLoadError("bad profile")

        with pytest.raises(ProfileLoadError, match="bad profile"):
            fail()

    def test_value_error_wrapped_in_analysis_error(self) -> None:
        """ValueError is wrapped in AnalysisError with the prefix message."""

        @wrap_errors("Spectral analysis failed")
        def fail() -> None:
            raise ValueError("negative frequency")

        with pytest.raises(
            AnalysisError, match="Spectral analysis failed: negative frequency"
        ):
            fail()

    def test_runtime_error_wrapped_with_cause(self) -> None:
        """RuntimeError is wrapped in AnalysisError with __cause__ set."""
        original = RuntimeError("something broke")

        @wrap_errors("Processing failed")
        def fail() -> None:
            raise original

        with pytest.raises(
            AnalysisError, match="Processing failed: something broke"
        ) as exc_info:
            fail()
        assert exc_info.value.__cause__ is original

    def test_preserves_function_name(self) -> None:
        """The decorated function preserves __name__ from the original."""

        @wrap_errors("Prefix")
        def my_analysis_function() -> None:
            pass

        assert my_analysis_function.__name__ == "my_analysis_function"

    def test_preserves_function_docstring(self) -> None:
        """The decorated function preserves __doc__ from the original."""

        @wrap_errors("Prefix")
        def my_func() -> None:
            """Analyze the spectrum."""
            pass

        assert my_func.__doc__ == "Analyze the spectrum."

    def test_works_with_args_and_kwargs(self) -> None:
        """The decorator works with functions that accept *args and **kwargs."""

        @wrap_errors("Prefix")
        def flexible(*args: object, **kwargs: object) -> tuple:
            return args, kwargs

        result = flexible(1, "two", key="value")
        assert result == ((1, "two"), {"key": "value"})


class TestGetEnvHelpers:
    """Tests for _get_env_int and _get_env_float helpers."""

    # -- _get_env_int --

    def test_get_env_int_returns_default_when_unset(self, monkeypatch) -> None:
        """Returns default when env var is not set."""
        monkeypatch.delenv("PHANTOM_MASKING_TOP_N", raising=False)
        assert _get_env_int("PHANTOM_MASKING_TOP_N", 10) == 10

    def test_get_env_int_returns_parsed_value(self, monkeypatch) -> None:
        """Returns parsed int when env var is set to a valid integer string."""
        monkeypatch.setenv("PHANTOM_MASKING_TOP_N", "5")
        assert _get_env_int("PHANTOM_MASKING_TOP_N", 10) == 5

    def test_get_env_int_raises_on_invalid(self, monkeypatch) -> None:
        """Raises AnalysisError when env var is not a valid integer."""
        monkeypatch.setenv("PHANTOM_MASKING_TOP_N", "abc")
        with pytest.raises(AnalysisError, match="must be an integer"):
            _get_env_int("PHANTOM_MASKING_TOP_N", 10)

    def test_get_env_int_returns_default_on_empty(self, monkeypatch) -> None:
        """Returns default when env var is empty string."""
        monkeypatch.setenv("PHANTOM_MASKING_TOP_N", "")
        assert _get_env_int("PHANTOM_MASKING_TOP_N", 10) == 10

    def test_get_env_int_returns_default_on_whitespace(self, monkeypatch) -> None:
        """Returns default when env var is whitespace only."""
        monkeypatch.setenv("PHANTOM_MASKING_TOP_N", "   ")
        assert _get_env_int("PHANTOM_MASKING_TOP_N", 10) == 10

    # -- _get_env_float --

    def test_get_env_float_returns_default_when_unset(self, monkeypatch) -> None:
        """Returns default when env var is not set."""
        monkeypatch.delenv("PHANTOM_PHAT_WINDOW_S", raising=False)
        assert _get_env_float("PHANTOM_PHAT_WINDOW_S", 10.0) == 10.0

    def test_get_env_float_returns_parsed_value(self, monkeypatch) -> None:
        """Returns parsed float when env var is set to a valid number string."""
        monkeypatch.setenv("PHANTOM_PHAT_WINDOW_S", "5.0")
        assert _get_env_float("PHANTOM_PHAT_WINDOW_S", 10.0) == 5.0

    def test_get_env_float_raises_on_invalid(self, monkeypatch) -> None:
        """Raises AnalysisError when env var is not a valid number."""
        monkeypatch.setenv("PHANTOM_PHAT_WINDOW_S", "abc")
        with pytest.raises(AnalysisError, match="must be a number"):
            _get_env_float("PHANTOM_PHAT_WINDOW_S", 10.0)

    def test_get_env_float_returns_default_on_empty(self, monkeypatch) -> None:
        """Returns default when env var is empty string."""
        monkeypatch.setenv("PHANTOM_PHAT_WINDOW_S", "")
        assert _get_env_float("PHANTOM_PHAT_WINDOW_S", 10.0) == 10.0

    def test_get_env_float_returns_default_on_whitespace(self, monkeypatch) -> None:
        """Returns default when env var is whitespace only."""
        monkeypatch.setenv("PHANTOM_PHAT_WINDOW_S", "   ")
        assert _get_env_float("PHANTOM_PHAT_WINDOW_S", 10.0) == 10.0


class TestAtomicWriteText:
    """atomic_write_text writes safely without a predictable temp file."""

    def test_writes_content(self, tmp_path):
        from phantom._utils import atomic_write_text

        target = tmp_path / "config.json"
        atomic_write_text(target, '{"ok": true}\n')
        assert target.read_text() == '{"ok": true}\n'

    def test_overwrites_existing(self, tmp_path):
        from phantom._utils import atomic_write_text

        target = tmp_path / "config.json"
        target.write_text("old")
        atomic_write_text(target, "new")
        assert target.read_text() == "new"

    def test_no_predictable_tmp_left_behind(self, tmp_path):
        from phantom._utils import atomic_write_text

        target = tmp_path / "config.json"
        atomic_write_text(target, "data")
        # The old predictable sibling must not exist, nor any leftover temp.
        assert not (tmp_path / "config.json.tmp").exists()
        assert list(tmp_path.iterdir()) == [target]

    def test_tmp_symlink_not_followed(self, tmp_path):
        """A pre-placed predictable temp symlink can't redirect the write."""
        from phantom._utils import atomic_write_text

        target = tmp_path / "config.json"
        outside = tmp_path / "outside.txt"
        outside.write_text("untouched")
        # Pre-place the old predictable temp name as a symlink to a victim file.
        (tmp_path / "config.json.tmp").symlink_to(outside)

        atomic_write_text(target, "safe")
        assert target.read_text() == "safe"
        assert outside.read_text() == "untouched"  # not clobbered
