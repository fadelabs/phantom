"""Tests for phantom version/update CLI commands."""

from __future__ import annotations

import importlib.metadata
import json
import subprocess
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from phantom.cli import cli
from phantom.cli.update import (
    CACHE_TTL_HOURS,
    _parse_version,
    check_for_update,
    is_editable_install,
)


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    """Redirect cache to tmp_path."""
    cache_file = tmp_path / "update-check.json"
    monkeypatch.setattr("phantom.cli.update.CACHE_DIR", tmp_path)
    monkeypatch.setattr("phantom.cli.update.CACHE_FILE", cache_file)
    return cache_file


def _mock_urlopen(data: dict | list, status: int = 200):
    """Create a mock urlopen context manager returning JSON data."""
    body = json.dumps(data).encode()
    resp = MagicMock()
    resp.status = status
    resp.read.return_value = body
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# ---------------------------------------------------------------------------
# _parse_version
# ---------------------------------------------------------------------------


class TestParseVersion:
    def test_with_v_prefix(self):
        assert _parse_version("v1.2.3") == (1, 2, 3)

    def test_without_prefix(self):
        assert _parse_version("1.2.3") == (1, 2, 3)

    def test_two_part(self):
        assert _parse_version("1.2") == (1, 2)

    def test_comparison_newer(self):
        assert _parse_version("1.2.0") > _parse_version("1.1.0")

    def test_comparison_equal(self):
        assert _parse_version("1.1.0") == _parse_version("1.1.0")

    def test_comparison_older(self):
        assert _parse_version("1.0.0") < _parse_version("1.1.0")

    def test_parse_version_prerelease_rc(self):
        # Regression: pre-release suffixes must not raise (P-11).
        assert _parse_version("1.2.3-rc1") == (1, 2, 3)

    def test_parse_version_prerelease_beta_pep440(self):
        assert _parse_version("1.2.0b1") == (1, 2, 0)

    def test_parse_version_prerelease_dashed_beta(self):
        assert _parse_version("2.0.0-beta") == (2, 0, 0)

    def test_parse_version_build_metadata(self):
        assert _parse_version("v1.2.3+build.5") == (1, 2, 3)

    def test_parse_version_prerelease_orders_below_next_release(self):
        # A suffixed latest tag must still compare cleanly against current.
        assert _parse_version("1.3.1") < _parse_version("1.4.0-rc1")
        assert _parse_version("1.3.1-rc1") <= _parse_version("1.3.1")


# ---------------------------------------------------------------------------
# is_editable_install
# ---------------------------------------------------------------------------


class TestIsEditableInstall:
    def test_editable_true(self):
        dist = MagicMock()
        dist.read_text.return_value = json.dumps(
            {"url": "file:///some/path", "dir_info": {"editable": True}}
        )
        with patch("importlib.metadata.distribution", return_value=dist):
            assert is_editable_install() is True

    def test_not_editable(self):
        dist = MagicMock()
        dist.read_text.return_value = json.dumps(
            {"url": "file:///some/path", "dir_info": {"editable": False}}
        )
        with patch("importlib.metadata.distribution", return_value=dist):
            assert is_editable_install() is False

    def test_no_direct_url(self):
        dist = MagicMock()
        dist.read_text.return_value = None
        with patch("importlib.metadata.distribution", return_value=dist):
            assert is_editable_install() is False

    def test_package_not_found(self):
        with patch(
            "importlib.metadata.distribution",
            side_effect=importlib.metadata.PackageNotFoundError("phantom-audio"),
        ):
            assert is_editable_install() is False


# ---------------------------------------------------------------------------
# check_for_update
# ---------------------------------------------------------------------------


class TestCheckForUpdate:
    def test_returns_none_on_network_failure(self, cache_dir):
        with patch("phantom.cli.update.urlopen", side_effect=OSError("no network")):
            assert check_for_update(force=True) is None

    def test_returns_none_on_urlerror(self, cache_dir):
        """A URLError network failure still degrades to None (P-21 narrowed catch)."""
        from urllib.error import URLError

        with patch(
            "phantom.cli.update.urlopen", side_effect=URLError("connection refused")
        ):
            assert check_for_update(force=True) is None

    def test_programming_error_is_not_swallowed(self, cache_dir):
        """The narrowed catch must let genuine bugs surface, not mask them (P-21).

        A TypeError (a stand-in for a programming error like the fixed P-11 parse
        bug) is outside the caught tuple, so it propagates instead of being
        silently turned into None.
        """
        with (
            patch(
                "phantom.cli.update._fetch_latest_version",
                side_effect=TypeError("unexpected programming bug"),
            ),
            pytest.raises(TypeError),
        ):
            check_for_update(force=True)

    def test_returns_versions_when_release_exists(self, cache_dir):
        resp = _mock_urlopen({"tag_name": "v1.2.0"})
        with patch("phantom.cli.update.urlopen", return_value=resp):
            result = check_for_update(force=True)
            assert result is not None
            latest, _current = result
            assert latest == "1.2.0"

    def test_falls_back_to_tags(self, cache_dir):
        call_count = 0

        def side_effect(req, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise OSError("404")
            return _mock_urlopen([{"name": "v1.3.0"}])

        with patch("phantom.cli.update.urlopen", side_effect=side_effect):
            result = check_for_update(force=True)
            assert result is not None
            assert result[0] == "1.3.0"

    def test_returns_none_when_no_releases_or_tags(self, cache_dir):
        with patch("phantom.cli.update.urlopen", side_effect=OSError("404")):
            assert check_for_update(force=True) is None

    def test_uses_fresh_cache(self, cache_dir):
        cache_dir.write_text(
            json.dumps(
                {
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                    "latest_version": "1.5.0",
                    "current_version": "1.1.0",
                }
            )
        )
        with patch("phantom.cli.update.urlopen") as mock_url:
            result = check_for_update(force=False)
            mock_url.assert_not_called()
            assert result == ("1.5.0", "1.1.0")

    def test_ignores_stale_cache(self, cache_dir):
        stale_time = datetime.now(timezone.utc) - timedelta(hours=CACHE_TTL_HOURS + 1)
        cache_dir.write_text(
            json.dumps(
                {
                    "checked_at": stale_time.isoformat(),
                    "latest_version": "1.5.0",
                    "current_version": "1.1.0",
                }
            )
        )
        resp = _mock_urlopen({"tag_name": "v1.6.0"})
        with patch("phantom.cli.update.urlopen", return_value=resp):
            result = check_for_update(force=False)
            assert result is not None
            assert result[0] == "1.6.0"

    def test_force_ignores_cache(self, cache_dir):
        cache_dir.write_text(
            json.dumps(
                {
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                    "latest_version": "1.5.0",
                    "current_version": "1.1.0",
                }
            )
        )
        resp = _mock_urlopen({"tag_name": "v1.7.0"})
        with patch("phantom.cli.update.urlopen", return_value=resp):
            result = check_for_update(force=True)
            assert result is not None
            assert result[0] == "1.7.0"

    def test_writes_cache_file(self, cache_dir):
        resp = _mock_urlopen({"tag_name": "v1.2.0"})
        with patch("phantom.cli.update.urlopen", return_value=resp):
            check_for_update(force=True)

        assert cache_dir.exists()
        data = json.loads(cache_dir.read_text())
        assert data["latest_version"] == "1.2.0"
        assert "checked_at" in data

    def test_handles_malformed_json_cache(self, cache_dir):
        cache_dir.write_text("not json")
        resp = _mock_urlopen({"tag_name": "v1.2.0"})
        with patch("phantom.cli.update.urlopen", return_value=resp):
            result = check_for_update(force=False)
            assert result is not None
            assert result[0] == "1.2.0"


# ---------------------------------------------------------------------------
# phantom version command
# ---------------------------------------------------------------------------


class TestVersionCommand:
    def test_help(self, runner):
        result = runner.invoke(cli, ["version", "--help"])
        assert result.exit_code == 0
        assert "version" in result.output.lower()

    def test_shows_info(self, runner, cache_dir):
        with patch("phantom.cli.update.check_for_update", return_value=None):
            result = runner.invoke(cli, ["version"])
            assert result.exit_code == 0
            assert "Phantom" in result.output
            assert "Python" in result.output

    def test_shows_update_available(self, runner, cache_dir):
        with patch(
            "phantom.cli.update.check_for_update",
            return_value=("2.0.0", "1.1.0"),
        ):
            result = runner.invoke(cli, ["version"])
            assert result.exit_code == 0
            assert "Update available" in result.output
            assert "2.0.0" in result.output

    def test_shows_up_to_date(self, runner, cache_dir):
        with patch(
            "phantom.cli.update.check_for_update",
            return_value=("1.1.0", "1.1.0"),
        ):
            result = runner.invoke(cli, ["version"])
            assert result.exit_code == 0
            assert "Up to date" in result.output

    def test_shows_unable_to_check(self, runner, cache_dir):
        with patch("phantom.cli.update.check_for_update", return_value=None):
            result = runner.invoke(cli, ["version"])
            assert result.exit_code == 0
            assert "Unable to check" in result.output

    def test_json_output(self, runner, cache_dir):
        with patch(
            "phantom.cli.update.check_for_update",
            return_value=("1.1.0", "1.1.0"),
        ):
            result = runner.invoke(cli, ["version", "--json"])
            data = json.loads(result.output)
            assert "version" in data
            assert "python" in data
            assert "update_available" in data


# ---------------------------------------------------------------------------
# phantom update command
# ---------------------------------------------------------------------------


class TestUpdateCommand:
    def test_help(self, runner):
        result = runner.invoke(cli, ["update", "--help"])
        assert result.exit_code == 0
        assert "Update" in result.output

    def test_already_current(self, runner, cache_dir):
        with patch(
            "phantom.cli.update.check_for_update",
            return_value=("1.1.0", "1.1.0"),
        ):
            result = runner.invoke(cli, ["update"])
            assert result.exit_code == 0
            assert "up to date" in result.output.lower()

    def test_check_failed(self, runner, cache_dir):
        with patch("phantom.cli.update.check_for_update", return_value=None):
            result = runner.invoke(cli, ["update"])
            assert result.exit_code != 0
            assert "Could not reach" in result.output

    def test_editable_install_warns(self, runner, cache_dir):
        with (
            patch(
                "phantom.cli.update.check_for_update",
                return_value=("2.0.0", "1.1.0"),
            ),
            patch("phantom.cli.update.is_editable_install", return_value=True),
        ):
            result = runner.invoke(cli, ["update"])
            assert result.exit_code == 0
            assert "editable" in result.output.lower()
            assert "git pull" in result.output

    def test_runs_uv_on_confirm(self, runner, cache_dir):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        with (
            patch(
                "phantom.cli.update.check_for_update",
                return_value=("2.0.0", "1.1.0"),
            ),
            patch("phantom.cli.update.is_editable_install", return_value=False),
            patch(
                "phantom.cli.update.subprocess.run", return_value=mock_proc
            ) as mock_run,
        ):
            result = runner.invoke(cli, ["update", "--yes"])
            assert result.exit_code == 0
            assert "Success" in result.output or "Updated" in result.output
            mock_run.assert_called_once()
            cmd = mock_run.call_args[0][0]
            assert "uv" in cmd[0] or cmd[0] == "uv"

    def test_cancelled_by_user(self, runner, cache_dir):
        with (
            patch(
                "phantom.cli.update.check_for_update",
                return_value=("2.0.0", "1.1.0"),
            ),
            patch("phantom.cli.update.is_editable_install", return_value=False),
        ):
            result = runner.invoke(cli, ["update"], input="n\n")
            assert result.exit_code == 0
            assert "cancelled" in result.output.lower()

    def test_uv_failure(self, runner, cache_dir):
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stderr = "ERROR: some uv error"
        with (
            patch(
                "phantom.cli.update.check_for_update",
                return_value=("2.0.0", "1.1.0"),
            ),
            patch("phantom.cli.update.is_editable_install", return_value=False),
            patch("phantom.cli.update.subprocess.run", return_value=mock_proc),
        ):
            result = runner.invoke(cli, ["update", "--yes"])
            assert result.exit_code != 0
            assert "Failed" in result.output

    def test_all_subprocess_calls_have_timeout(self, runner, cache_dir):
        """Every uv subprocess call in `update` must pass a timeout (P-16)."""
        recorded_kwargs = []

        def fake_run(cmd, **kwargs):
            recorded_kwargs.append(kwargs)
            proc = MagicMock()
            # First call (upgrade) triggers the list + install fallback path so
            # all three subprocess calls are exercised.
            if cmd[:3] == ["uv", "tool", "upgrade"]:
                proc.returncode = 1
                proc.stderr = "error: no such command 'upgrade'"
            else:
                proc.returncode = 0
                proc.stdout = "phantom-audio v1.1.0 (/path)\n"
                proc.stderr = ""
            return proc

        with (
            patch(
                "phantom.cli.update.check_for_update",
                return_value=("2.0.0", "1.1.0"),
            ),
            patch("phantom.cli.update.is_editable_install", return_value=False),
            patch("phantom.cli.update.subprocess.run", side_effect=fake_run),
        ):
            runner.invoke(cli, ["update", "--yes"])

        assert recorded_kwargs, "expected subprocess.run to be called"
        for kwargs in recorded_kwargs:
            assert "timeout" in kwargs, f"missing timeout in call kwargs: {kwargs}"

    def test_no_such_command_triggers_extras_preserving_reinstall(
        self, runner, cache_dir
    ):
        """Pin the string-match fallback: "no such command" -> list + install (P-18).

        This locks the CURRENT (intentionally deferred) detection behavior. If uv
        reworded its error, this test breaks -- which is the signal that the
        fallback needs revisiting rather than silently disabling.
        """
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            proc = MagicMock()
            if cmd[:3] == ["uv", "tool", "upgrade"]:
                proc.returncode = 1
                proc.stderr = "error: no such command 'upgrade'"
            else:
                proc.returncode = 0
                proc.stdout = "phantom-audio v1.1.0 (/path)\n"
                proc.stderr = ""
            return proc

        with (
            patch(
                "phantom.cli.update.check_for_update",
                return_value=("2.0.0", "1.1.0"),
            ),
            patch("phantom.cli.update.is_editable_install", return_value=False),
            patch("phantom.cli.update.subprocess.run", side_effect=fake_run),
        ):
            result = runner.invoke(cli, ["update", "--yes"])

        assert result.exit_code == 0
        # Fallback fired: upgrade, then list, then force-install.
        assert calls[0][:3] == ["uv", "tool", "upgrade"]
        assert any(c[:3] == ["uv", "tool", "list"] for c in calls)
        assert any(c[:3] == ["uv", "tool", "install"] for c in calls)

    def test_other_uv_error_does_not_trigger_reinstall(self, runner, cache_dir):
        """A nonzero exit WITHOUT "no such command" must NOT fire the fallback (P-18).

        Pins the specificity of the string match: only the exact uv wording
        triggers the extras-preserving reinstall.
        """
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            proc = MagicMock()
            proc.returncode = 1
            proc.stderr = "error: some other failure"
            proc.stdout = ""
            return proc

        with (
            patch(
                "phantom.cli.update.check_for_update",
                return_value=("2.0.0", "1.1.0"),
            ),
            patch("phantom.cli.update.is_editable_install", return_value=False),
            patch("phantom.cli.update.subprocess.run", side_effect=fake_run),
        ):
            result = runner.invoke(cli, ["update", "--yes"])

        assert result.exit_code != 0
        # Only the single upgrade call was made; no list/install fallback.
        assert calls == [["uv", "tool", "upgrade", "phantom-audio"]]

    def test_timeout_renders_update_failed(self, runner, cache_dir):
        """A subprocess timeout surfaces the Update Failed panel, not a hang (P-16)."""
        with (
            patch(
                "phantom.cli.update.check_for_update",
                return_value=("2.0.0", "1.1.0"),
            ),
            patch("phantom.cli.update.is_editable_install", return_value=False),
            patch(
                "phantom.cli.update.subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd="uv", timeout=120),
            ),
        ):
            result = runner.invoke(cli, ["update", "--yes"])
            assert result.exit_code != 0
            assert "Failed" in result.output


# ---------------------------------------------------------------------------
# Startup hook
# ---------------------------------------------------------------------------


class TestStartupHook:
    def test_shows_update_notice(self, runner, cache_dir):
        with patch(
            "phantom.cli.update.check_for_update",
            return_value=("2.0.0", "1.1.0"),
        ):
            result = runner.invoke(cli, ["doctor", "--help"])
            assert "Update available" in result.output

    def test_silent_when_up_to_date(self, runner, cache_dir):
        with patch(
            "phantom.cli.update.check_for_update",
            return_value=("1.1.0", "1.1.0"),
        ):
            result = runner.invoke(cli, ["doctor", "--help"])
            assert "Update available" not in result.output

    def test_silent_on_failure(self, runner, cache_dir):
        with patch("phantom.cli.update.check_for_update", return_value=None):
            result = runner.invoke(cli, ["doctor", "--help"])
            assert "Update available" not in result.output


class TestInstalledPackageSpec:
    """Extras parsed from `uv tool list` are allowlisted before reuse."""

    def test_valid_extras_preserved(self):
        from phantom.cli.update import _installed_package_spec

        out = "phantom-audio[separation,processing] v1.3.0 (/path)\n"
        assert _installed_package_spec(out) == "phantom-audio[separation,processing]"

    def test_unknown_extras_dropped(self):
        from phantom.cli.update import _installed_package_spec

        out = "phantom-audio[evil,separation] v1.3.0 (/path)\n"
        # Only the known extra survives; the crafted one is dropped.
        assert _installed_package_spec(out) == "phantom-audio[separation]"

    def test_all_unknown_falls_back_to_bare(self):
        from phantom.cli.update import _installed_package_spec

        out = "phantom-audio[../../etc/passwd] v1.3.0 (/path)\n"
        assert _installed_package_spec(out) == "phantom-audio"

    def test_no_extras_returns_bare(self):
        from phantom.cli.update import _installed_package_spec

        out = "phantom-audio v1.3.0 (/path)\n"
        assert _installed_package_spec(out) == "phantom-audio"
