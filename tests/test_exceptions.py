"""Tests for the Phantom exception hierarchy."""

import pytest

from phantom.exceptions import (
    AnalysisError,
    AudioLoadError,
    DependencyMissingError,
    PathSecurityError,
    PhantomError,
)


class TestPhantomError:
    """PhantomError is the base exception for all Phantom errors."""

    def test_is_subclass_of_exception(self):
        assert issubclass(PhantomError, Exception)

    def test_can_be_raised_and_caught(self):
        with pytest.raises(PhantomError):
            raise PhantomError("something went wrong")


class TestAudioLoadError:
    """AudioLoadError is raised when an audio file cannot be loaded."""

    def test_is_subclass_of_phantom_error(self):
        assert issubclass(AudioLoadError, PhantomError)

    def test_message_preserved(self):
        err = AudioLoadError("file.wav is corrupt")
        assert str(err) == "file.wav is corrupt"

    def test_caught_by_phantom_error(self):
        with pytest.raises(PhantomError):
            raise AudioLoadError("unsupported format")


class TestAnalysisError:
    """AnalysisError is raised when an analysis algorithm fails."""

    def test_is_subclass_of_phantom_error(self):
        assert issubclass(AnalysisError, PhantomError)

    def test_caught_by_phantom_error(self):
        with pytest.raises(PhantomError):
            raise AnalysisError("spectral analysis failed")


class TestPathSecurityError:
    """PathSecurityError is raised when a file path violates security restrictions."""

    def test_is_subclass_of_phantom_error(self):
        assert issubclass(PathSecurityError, PhantomError)

    def test_message_preserved(self):
        err = PathSecurityError("outside allowed directory")
        assert str(err) == "outside allowed directory"

    def test_caught_by_phantom_error(self):
        with pytest.raises(PhantomError):
            raise PathSecurityError("path violation")


class TestDependencyMissingError:
    """DependencyMissingError is raised when an optional dep is missing."""

    def test_is_subclass_of_phantom_error(self):
        assert issubclass(DependencyMissingError, PhantomError)

    def test_message_contains_package_name(self):
        err = DependencyMissingError("demucs", "separation")
        assert "demucs is not installed" in str(err)

    def test_message_contains_pip_install_command(self):
        err = DependencyMissingError("demucs", "separation")
        assert 'uv tool install "phantom-audio[separation]"' in str(err)

    def test_detail_appended_to_message(self):
        err = DependencyMissingError(
            "demucs", "separation", detail="Required for stem separation."
        )
        msg = str(err)
        assert "demucs is not installed" in msg
        assert 'uv tool install "phantom-audio[separation]"' in msg
        assert "Required for stem separation." in msg

    def test_caught_by_phantom_error(self):
        with pytest.raises(PhantomError):
            raise DependencyMissingError("matchering", "matching")

    def test_package_and_extra_attributes(self):
        err = DependencyMissingError("demucs", "separation")
        assert err.package == "demucs"
        assert err.extra == "separation"


class TestTopLevelImports:
    """All four exception classes are importable from the top-level phantom package."""

    def test_import_from_phantom(self):
        from phantom import (
            AnalysisError,
            AudioLoadError,
            DependencyMissingError,
            PathSecurityError,
            PhantomError,
        )

        # Verify they are the same classes
        assert PhantomError is not None
        assert PathSecurityError is not None
        assert AudioLoadError is not None
        assert AnalysisError is not None
        assert DependencyMissingError is not None
