#!/usr/bin/env python3
"""Verify install.ps1's telemetry payload.

Runs the real Send-Ping and Stop-Install functions from install.ps1 with the
outbound HTTP call stubbed, then asserts every payload against the Phase 9 spec
and the validation rules in fadelab.net's api/ping.ts.

    python3 tests/install_ps1/verify_telemetry.py

Uses whatever PowerShell it can find: $PWSH, then pwsh, then powershell. Set
PWSH=powershell on Windows to exercise Windows PowerShell 5.1 specifically,
which is the runtime real users install under. With no PowerShell on the host
it falls back to Docker, which is how this runs on macOS.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
INSTALL_PS1 = REPO / "install.ps1"

SCENARIOS = [
    "started",
    "complete",
    "complete-core",
    "optout",
    "dirty-values",
    "failed-os",
    "failed-uv",
    "failed-pkg",
    "failed-path",
]

ALLOWED_EVENTS = {"install_started", "install_complete", "install_failed"}
REASON_SHAPE = re.compile(r"^[a-z0-9_]{1,64}$")
SAFE_CHARSET = re.compile(r"^[A-Za-z0-9._,+-]+$")
REQUIRED = ["event", "iid", "os", "arch", "version", "extras", "method"]

DOCKER_IMAGE = "mcr.microsoft.com/powershell:latest"


def find_runner() -> tuple[str, list[str]]:
    """Return (label, argv prefix) for invoking a PowerShell script."""
    explicit = os.environ.get("PWSH")
    if explicit:
        return explicit, [explicit, "-NoProfile", "-File"]
    for exe in ("pwsh", "powershell"):
        if shutil.which(exe):
            return exe, [exe, "-NoProfile", "-File"]
    if shutil.which("docker"):
        return f"docker ({DOCKER_IMAGE})", [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{REPO}:/repo:ro",
            DOCKER_IMAGE,
            "pwsh",
            "-NoProfile",
            "-File",
        ]
    sys.exit("No PowerShell found. Install pwsh, or Docker, or set PWSH.")


LABEL, PREFIX = find_runner()
IN_DOCKER = PREFIX[0] == "docker"


def run_script(script: str, *args: str) -> str:
    if IN_DOCKER:
        script_arg = f"/repo/tests/install_ps1/{script}"
        install_arg = "/repo/install.ps1"
    else:
        script_arg = str(HERE / script)
        install_arg = str(INSTALL_PS1)
    cmd = [*PREFIX, script_arg, *args, "-InstallScript", install_arg]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    # Failure sites exit 1 by design, so a nonzero code is not itself an error.
    return proc.stdout + proc.stderr


def collect() -> tuple[dict[str, list[dict]], dict[str, str]]:
    pings: dict[str, list[dict]] = {}
    for scenario in SCENARIOS:
        out = run_script("scenario.ps1", "-Scenario", scenario)
        bodies = []
        for line in out.splitlines():
            if line.startswith("CAPTURED|"):
                _, method, uri, body = line.strip().split("|", 3)
                bodies.append({"method": method, "uri": uri, "json": json.loads(body)})
        pings[scenario] = bodies

    exprs: dict[str, str] = {}
    for line in run_script("exprs.ps1").splitlines():
        if line.startswith("EXPR|"):
            _, label, value = line.strip().split("|", 2)
            exprs[label] = value
    return pings, exprs


passed = 0
failures: list[str] = []


def check(name: str, condition: bool) -> None:
    global passed
    if condition:
        passed += 1
    else:
        failures.append(name)


def main() -> int:
    print(f"\n  install.ps1 telemetry — running under {LABEL}\n")
    pings, exprs = collect()

    if not any(pings.values()):
        return fail_out("No pings captured at all — the harness did not run.")

    # ── Transport and the endpoint's contract, for every payload ──
    for scenario, calls in pings.items():
        for call in calls:
            body = call["json"]
            check(f"{scenario}: uses POST", call["method"] == "Post")
            check(
                f"{scenario}: posts to /api/ping",
                call["uri"] == "https://fadelab.net/api/ping",
            )
            check(f"{scenario}: event allowlisted", body.get("event") in ALLOWED_EVENTS)
            check(
                f"{scenario}: all required fields present",
                all(k in body for k in REQUIRED),
            )
            check(f"{scenario}: method=uv", body.get("method") == "uv")
            check(f"{scenario}: os=windows", body.get("os") == "windows")
            check(f"{scenario}: iid present", bool(body.get("iid")))
            check(
                f"{scenario}: no value exceeds the endpoint's 64-char cap",
                all(len(str(v)) <= 64 for v in body.values()),
            )
            check(
                f"{scenario}: values stay in the safe charset",
                all(SAFE_CHARSET.match(str(v)) for k, v in body.items() if k != "iid"),
            )

    # ── Success events ──
    started = pings["started"][0]["json"]
    check("started: exactly one ping", len(pings["started"]) == 1)
    check("started: event", started["event"] == "install_started")
    check("started: arch normalized", started["arch"] == "x86_64")
    check(
        "started: extras=none before any install attempt", started["extras"] == "none"
    )
    check("started: version defaults to unknown", started["version"] == "unknown")
    check("started: no reason on success", "reason" not in started)

    complete = pings["complete"][0]["json"]
    check("complete: event", complete["event"] == "install_complete")
    check("complete: bare version", complete["version"] == "1.5.0")
    check("complete: extras=all", complete["extras"] == "all")
    check("complete: no reason on success", "reason" not in complete)

    core = pings["complete-core"][0]["json"]
    check("core fallback: extras=none", core["extras"] == "none")
    check("core fallback: arm64 carried through", core["arch"] == "arm64")

    # ── Failure sites ──
    sites = {
        "failed-os": ("unsupported_os", "none"),
        "failed-uv": ("uv_install_failed", "none"),
        "failed-pkg": ("pkg_install_failed", "all"),
        "failed-path": ("not_on_path", "all"),
    }
    for scenario, (code, extras) in sites.items():
        calls = pings[scenario]
        check(f"{scenario}: exactly one ping", len(calls) == 1)
        body = calls[0]["json"]
        check(f"{scenario}: event=install_failed", body["event"] == "install_failed")
        check(f"{scenario}: reason={code}", body.get("reason") == code)
        check(
            f"{scenario}: reason matches the endpoint's shape",
            bool(REASON_SHAPE.match(body.get("reason", ""))),
        )
        check(f"{scenario}: version=unknown", body["version"] == "unknown")
        check(f"{scenario}: extras={extras}", body["extras"] == extras)

    check(
        "unsupported_os reports before arch detection",
        pings["failed-os"][0]["json"]["arch"] == "unknown",
    )

    # ── Opt-out ──
    check("PHANTOM_NO_TELEMETRY=1 sends nothing", pings["optout"] == [])

    # ── Charset filter ──
    dirty = pings["dirty-values"][0]["json"]
    check("dirty version sanitized", bool(SAFE_CHARSET.match(dirty["version"])))
    check("dirty version drops quotes", '"' not in dirty["version"])
    check("dirty version drops non-ASCII", dirty["version"].isascii())

    # ── Inline expressions, lifted from the shipped source ──
    check("arch switch located in source", exprs.get("arch-block-found") == "YES")
    check(
        "version expression located in source", exprs.get("version-expr-found") == "YES"
    )
    for case, expected in [
        ("X64", "x86_64"),
        ("Amd64", "x86_64"),
        ("Arm64", "arm64"),
        ("X86", "x86"),
    ]:
        check(f"arch {case} -> {expected}", exprs.get(f"arch:{case}") == expected)
    for case, expected in [
        ("phantom, version 1.5.0", "1.5.0"),
        ("phantom, version 1.5.0rc1", "1.5.0rc1"),
        ("", "unknown"),
        ("garbage output", "unknown"),
    ]:
        check(
            f"version {case!r} -> {expected}", exprs.get(f"version:{case}") == expected
        )

    # ── The two state transitions the harness assumes, grounded in the source ──
    src = INSTALL_PS1.read_text()
    check(
        'source initializes extras to "none"',
        '$script:InstallExtras = "none"' in src.split("Windows version check")[0],
    )
    check(
        'source sets extras to "all" before the full install attempt',
        re.search(
            r'\$script:InstallExtras = "all"\s*\n\s*\$installLog = & \$uvPath tool install '
            r'"phantom-audio\[all\]"',
            src,
        )
        is not None,
    )

    if failures:
        return fail_out(None)
    print(f"  {passed} passed, 0 failed\n")
    return 0


def fail_out(message: str | None) -> int:
    if message:
        print(f"  {message}\n")
    print(f"  {passed} passed, {len(failures)} failed\n")
    for name in failures:
        print(f"  FAIL  {name}")
    print()
    return 1


if __name__ == "__main__":
    sys.exit(main())
