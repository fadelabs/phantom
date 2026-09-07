"""Regression checks for files that must never enter public package archives."""

import runpy
from pathlib import Path

import pytest

check = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts/check-release-artifacts.py")
)["check"]


@pytest.mark.parametrize(
    "name",
    [
        "phantom_audio-1.6.0/.hypothesis/constants/cache",
        "phantom_audio-1.6.0/.mcp.json",
        "phantom_audio-1.6.0/.planning/STATE.md",
        "phantom_audio-1.6.0/src/phantom/../../private.txt",
    ],
)
def test_local_files_and_traversal_are_rejected(name):
    with pytest.raises(ValueError):
        check(name, b"local content", wheel=False)


def test_local_home_paths_in_package_metadata_are_rejected():
    payload = b"/" + b"Users" + b"/example/private-file"
    with pytest.raises(ValueError, match="Local home path"):
        check("phantom_audio-1.6.0/PKG-INFO", payload, wheel=False)


def test_packaged_profile_is_allowed():
    check("phantom/profiles/rock.json", b'{"name": "rock"}', wheel=True)
