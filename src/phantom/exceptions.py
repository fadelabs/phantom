"""Phantom exception hierarchy.

All Phantom errors inherit from PhantomError, allowing callers to catch
any Phantom-specific failure with a single except clause.

Error messages are written in plain English for musicians (D-08).
"""


class PhantomError(Exception):
    """Base exception for all Phantom errors."""

    pass


class AudioLoadError(PhantomError):
    """Raised when an audio file cannot be loaded or is unsupported."""

    pass


class AnalysisError(PhantomError):
    """Raised when an analysis algorithm fails."""

    pass


class ProfileLoadError(PhantomError):
    """Raised when a reference profile cannot be loaded or is malformed."""

    pass


class PathSecurityError(PhantomError):
    """Raised when a file path violates security restrictions."""

    pass


class DependencyMissingError(PhantomError):
    """Raised when an optional dependency is not installed.

    Message includes a copy-pasteable install command.
    """

    def __init__(self, package: str, extra: str, detail: str = "") -> None:
        self.package = package
        self.extra = extra
        msg = f'{package} is not installed. Install it with: uv tool install "phantom-audio[{extra}]" --python 3.13'
        if detail:
            msg += f"\n{detail}"
        super().__init__(msg)
