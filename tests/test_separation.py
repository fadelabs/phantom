"""Tests for the stem separation dispatch shim (issue #7).

The Demucs implementation lives in the sibling distribution
phantom-audio-separation (packages/phantom-audio-separation), where its
behavior tests live too. These tests cover the thin shim in
phantom.separation: entry-point discovery, dispatch, the
DependencyMissingError install hint when no plugin is installed, and the
core-metadata guarantee that no torch/demucs dependency leaks into
phantom-audio itself.
"""

import sys
from importlib.metadata import entry_points
from pathlib import Path

import pytest

import phantom.separation as separation_mod
from phantom.exceptions import DependencyMissingError
from phantom.separation import (
    SEPARATION_EP_GROUP,
    SeparationResult,
    _load_backend,
    separate_stems,
)

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def _plugin_installed() -> bool:
    """True when a phantom.separation entry point is present."""
    return bool(list(entry_points(group=SEPARATION_EP_GROUP)))


class _FakeEntryPoint:
    """Minimal stand-in for importlib.metadata.EntryPoint."""

    def __init__(self, target):
        self._target = target
        self.name = "fake"

    def load(self):
        return self._target


class TestMissingPlugin:
    """Without the plugin installed, the shim raises with the install hint."""

    @pytest.mark.skipif(
        _plugin_installed(),
        reason="phantom-audio-separation is installed -- test requires it absent",
    )
    def test_missing_plugin_raises_dependency_error(self, tmp_path):
        """No plugin -> DependencyMissingError with the [separation] hint."""
        with pytest.raises(DependencyMissingError) as exc_info:
            separate_stems("any.wav", str(tmp_path / "out"))
        assert 'uv tool install "phantom-audio[separation]"' in str(exc_info.value)
        assert "phantom-audio-separation" in str(exc_info.value)

    def test_no_entry_points_raises_dependency_error(self, monkeypatch, tmp_path):
        """Even with a plugin installed, an empty group raises the hint."""
        monkeypatch.setattr(separation_mod, "entry_points", lambda group: [])
        with pytest.raises(DependencyMissingError) as exc_info:
            separate_stems("any.wav", str(tmp_path / "out"))
        assert 'uv tool install "phantom-audio[separation]"' in str(exc_info.value)


class TestDispatch:
    """The shim dispatches to the discovered backend unchanged."""

    def test_dispatch_passes_args_and_returns_result(self, monkeypatch, tmp_path):
        """Backend receives the shim's args; its result passes through."""
        calls = []
        expected = SeparationResult(stems={"vocals": "/out/vocals.wav"})

        def fake_backend(input_path, output_dir):
            calls.append((input_path, output_dir))
            return expected

        monkeypatch.setattr(separation_mod, "_load_backend", lambda: fake_backend)

        result = separate_stems("mix.wav", str(tmp_path / "stems"))

        assert result is expected
        assert calls == [("mix.wav", str(tmp_path / "stems"))]

    def test_backend_phantom_error_passes_through(self, monkeypatch, tmp_path):
        """A PhantomError raised by the backend is not double-wrapped."""

        def fake_backend(input_path, output_dir):
            raise DependencyMissingError(package="Demucs", extra="separation")

        monkeypatch.setattr(separation_mod, "_load_backend", lambda: fake_backend)

        with pytest.raises(DependencyMissingError, match="Demucs is not installed"):
            separate_stems("mix.wav", str(tmp_path / "stems"))


class TestEntryPointDiscovery:
    """_load_backend discovers backends via the phantom.separation group."""

    def test_load_backend_returns_first_entry_point(self, monkeypatch):
        """The first entry point in the group is loaded and returned."""
        sentinel = object()

        def fake_entry_points(group):
            assert group == SEPARATION_EP_GROUP
            return [_FakeEntryPoint(sentinel), _FakeEntryPoint(object())]

        monkeypatch.setattr(separation_mod, "entry_points", fake_entry_points)
        assert _load_backend() is sentinel

    def test_load_backend_returns_none_when_no_plugins(self, monkeypatch):
        """An empty entry-point group yields None."""
        monkeypatch.setattr(separation_mod, "entry_points", lambda group: [])
        assert _load_backend() is None


class TestCoreMetadata:
    """phantom-audio's own dependency metadata carries no torch/demucs."""

    @pytest.fixture(scope="class")
    def project(self):
        pyproject = Path(__file__).parents[1] / "pyproject.toml"
        with open(pyproject, "rb") as fh:
            return tomllib.load(fh)["project"]

    def test_no_torch_in_core_dependencies(self, project):
        """Core dependencies never mention torch, torchaudio, or demucs."""
        for dep in project["dependencies"]:
            for banned in ("torch", "torchaudio", "demucs"):
                assert banned not in dep.lower(), f"{banned} leaked into core: {dep}"

    def test_no_torch_in_any_extra(self, project):
        """No optional extra depends on torch/torchaudio/demucs directly."""
        for extra, deps in project["optional-dependencies"].items():
            for dep in deps:
                for banned in ("torch", "torchaudio", "demucs"):
                    assert banned not in dep.lower(), (
                        f"{banned} leaked into extra '{extra}': {dep}"
                    )

    def test_separation_extra_is_meta_installer(self, project):
        """[separation] pulls exactly the sibling plugin distribution."""
        assert project["optional-dependencies"]["separation"] == [
            "phantom-audio-separation"
        ]
