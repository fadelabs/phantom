"""Tests for phantom._utils shared helpers."""

from __future__ import annotations

import os

import numpy as np
import pytest

from phantom._utils import _block_rms_db, validate_input_path, validate_output_path, wrap_errors
from phantom.exceptions import (
    AnalysisError,
    AudioLoadError,
    DependencyMissingError,
    PathSecurityError,
    PhantomError,
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


class TestValidateOutputPath:
    """Tests for validate_output_path() -- SEC-02 output containment."""

    def test_unrestricted_when_env_unset(self, monkeypatch) -> None:
        """Returns path unchanged when PHANTOM_OUTPUT_DIR is not set (D-11)."""
        monkeypatch.delenv("PHANTOM_OUTPUT_DIR", raising=False)
        result = validate_output_path("/any/output/path")
        assert result == "/any/output/path"

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

        with pytest.raises(AnalysisError, match="Spectral analysis failed: negative frequency"):
            fail()

    def test_runtime_error_wrapped_with_cause(self) -> None:
        """RuntimeError is wrapped in AnalysisError with __cause__ set."""
        original = RuntimeError("something broke")

        @wrap_errors("Processing failed")
        def fail() -> None:
            raise original

        with pytest.raises(AnalysisError, match="Processing failed: something broke") as exc_info:
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
