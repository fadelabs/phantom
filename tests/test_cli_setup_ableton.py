"""Ableton setup preserves configuration and uses the matching upstream script."""

import json
from unittest.mock import patch

from click.testing import CliRunner

from phantom.cli.setup_ableton import ABLETON_PACKAGE, setup_ableton


def test_config_only_preserves_other_servers_and_is_idempotent(tmp_path):
    target = tmp_path / "mcp.json"
    original = {"mcpServers": {"reaper": {"command": "reaper"}}, "other": 42}
    target.write_text(json.dumps(original))
    with (
        patch("phantom.cli.setup_ableton.shutil.which", return_value="/bin/uvx"),
        patch("phantom.cli.setup_ableton.subprocess.run") as run,
    ):
        runner = CliRunner()
        args = ["--config", str(target), "--config-only", "--json"]
        first = runner.invoke(setup_ableton, args)
        second = runner.invoke(setup_ableton, args)
    assert first.exit_code == second.exit_code == 0, first.output
    run.assert_not_called()
    data = json.loads(target.read_text())
    assert data["other"] == 42
    assert data["mcpServers"]["reaper"] == original["mcpServers"]["reaper"]
    entry = data["mcpServers"]["AbletonMCP"]
    assert entry["args"] == ["--from", ABLETON_PACKAGE, "ableton-mcp"]
    assert entry["env"]["ABLETON_MCP_DISABLE_TELEMETRY"] == "true"
    assert json.loads(first.output)["live_connection"] == "not_verified"


def test_refuses_conflicting_config_before_installing(tmp_path):
    target = tmp_path / "mcp.json"
    original = '{"mcpServers":{"AbletonMCP":{"command":"custom"}}}'
    target.write_text(original)
    with (
        patch("phantom.cli.setup_ableton.shutil.which", return_value="uvx"),
        patch("phantom.cli.setup_ableton.subprocess.run") as run,
    ):
        result = CliRunner().invoke(setup_ableton, ["--config", str(target)])
    assert result.exit_code != 0
    assert "--force" in result.output
    run.assert_not_called()
    assert target.read_text() == original


def test_script_install_failure_does_not_write_config(tmp_path):
    target = tmp_path / "mcp.json"
    with (
        patch("phantom.cli.setup_ableton.shutil.which", return_value="uvx"),
        patch("phantom.cli.setup_ableton.subprocess.run") as run,
    ):
        run.return_value.returncode = 1
        run.return_value.stderr = "install failed"
        result = CliRunner().invoke(
            setup_ableton,
            [
                "--config",
                str(target),
                "--scripts-dir",
                str(tmp_path / "Remote Scripts"),
            ],
        )
    assert result.exit_code != 0
    assert not target.exists()
    assert run.call_args.args[0][:4] == [
        "uvx",
        "--from",
        ABLETON_PACKAGE,
        "ableton-mcp-install-script",
    ]
    assert run.call_args.kwargs["env"]["ABLETON_MCP_DISABLE_TELEMETRY"] == "true"


def test_invalid_config_is_not_replaced(tmp_path):
    target = tmp_path / "mcp.json"
    target.write_text('{"mcpServers": []}')
    with patch("phantom.cli.setup_ableton.shutil.which", return_value="uvx"):
        result = CliRunner().invoke(
            setup_ableton, ["--config", str(target), "--config-only"]
        )
    assert result.exit_code != 0
    assert target.read_text() == '{"mcpServers": []}'


def test_full_setup_restricts_installed_listener(tmp_path):
    from pathlib import Path

    target = tmp_path / "mcp.json"
    scripts = tmp_path / "Remote Scripts"

    def installer(*arguments):
        assert arguments[0] == "--target"
        script = Path(arguments[1]) / "AbletonMCP" / "__init__.py"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text('HOST = "0.0.0.0"\nDEFAULT_PORT = 9877\n')
        return "installed"

    with (
        patch("phantom.cli.setup_ableton.shutil.which", return_value="uvx"),
        patch("phantom.cli.setup_ableton._run_script_installer", side_effect=installer),
    ):
        result = CliRunner().invoke(
            setup_ableton,
            ["--config", str(target), "--scripts-dir", str(scripts), "--json"],
        )
    assert result.exit_code == 0, result.output
    source = (scripts / "AbletonMCP" / "__init__.py").read_text()
    assert 'HOST = "127.0.0.1"' in source
    assert "0.0.0.0" not in source
    assert json.loads(result.output)["listener_host"] == "127.0.0.1"


def test_unknown_listener_does_not_write_client_configuration(tmp_path):
    scripts = tmp_path / "Remote Scripts"
    script = scripts / "AbletonMCP" / "__init__.py"
    script.parent.mkdir(parents=True)
    script.write_text('HOST = "unexpected"\n')
    target = tmp_path / "mcp.json"
    with (
        patch("phantom.cli.setup_ableton.shutil.which", return_value="uvx"),
        patch(
            "phantom.cli.setup_ableton._run_script_installer", return_value="installed"
        ),
    ):
        result = CliRunner().invoke(
            setup_ableton, ["--config", str(target), "--scripts-dir", str(scripts)]
        )
    assert result.exit_code != 0
    assert "Cannot verify" in result.output
    assert not target.exists()


def test_default_setup_restricts_every_discovered_library(tmp_path):
    from phantom.cli.setup_ableton import _install_script

    roots = [tmp_path / "Library One", tmp_path / "Library Two"]
    for root in roots:
        script = root / "AbletonMCP" / "__init__.py"
        script.parent.mkdir(parents=True)
        script.write_text('HOST = "0.0.0.0"\n')

    def installer(*arguments):
        return (
            "\n".join(map(str, roots))
            if arguments == ("--list-targets",)
            else "installed"
        )

    with patch(
        "phantom.cli.setup_ableton._run_script_installer", side_effect=installer
    ):
        _install_script(None)
    assert all(
        'HOST = "127.0.0.1"' in (root / "AbletonMCP" / "__init__.py").read_text()
        for root in roots
    )
