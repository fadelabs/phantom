# Runs one install.ps1 telemetry scenario with the outbound HTTP call stubbed,
# printing "CAPTURED|<method>|<uri>|<body>" for each ping the script attempts.
# Driven by verify_telemetry.py; see that file for the assertions.
param(
    [Parameter(Mandatory)][string]$Scenario,
    [string]$InstallScript = (Join-Path $PSScriptRoot '../../install.ps1')
)

$src = Get-Content $InstallScript -Raw

# Drop the bottom-of-file `Main` invocation so sourcing only defines functions.
$src = $src -replace '(?m)^Main\s*$', ''
# Drop the TLS line. It is Windows-only, and irrelevant here because the
# network call is stubbed out below.
$src = $src -replace '(?m)^\[Net\.ServicePointManager\].*$', ''

Invoke-Expression $src

# Stub the outbound call. A function shadows the real cmdlet at call time.
function Invoke-WebRequest {
    param(
        [string]$Uri, [string]$Method, [string]$ContentType, [string]$Body,
        [switch]$UseBasicParsing, [int]$TimeoutSec, [string]$ErrorAction
    )
    Write-Host "CAPTURED|$Method|$Uri|$Body"
}

# What Main sets before any ping can fire. Each scenario then advances the
# state to whatever Main would hold at that point in a real run.
$script:InstallId = "11111111-2222-3333-4444-555555555555"
$script:InstallExtras = "none"
$script:PingOs = "windows"
$script:PingArch = "unknown"

switch ($Scenario) {
    'started' {
        # After arch detection, before the install attempt.
        $script:PingArch = "x86_64"
        Send-Ping "install_started"
    }
    'complete' {
        # Full install succeeded, so extras was set before the attempt.
        $script:PingArch = "x86_64"
        $script:InstallExtras = "all"
        Send-Ping "install_complete" "1.5.0"
    }
    'complete-core' {
        # Full install failed, core fallback succeeded and reset extras.
        $script:PingArch = "arm64"
        $script:InstallExtras = "none"
        Send-Ping "install_complete" "1.5.0"
    }
    'optout' {
        $env:PHANTOM_NO_TELEMETRY = "1"
        $script:PingArch = "x86_64"
        Send-Ping "install_started"
        Send-Ping "install_complete" "1.5.0"
        Stop-Install "should not report" "pkg_install_failed"
    }
    'dirty-values' {
        # Spaces, quotes, braces and non-ASCII must not reach the payload.
        $script:PingArch = "x86_64"
        $script:InstallExtras = "all"
        # The non-ASCII char is built rather than typed so this file stays pure
        # ASCII — Windows PowerShell 5.1 reads a BOM-less .ps1 as ANSI.
        Send-Ping "install_complete" ('phantom, version 1.5.0 "quoted" {brace} caf' + [char]0xE9)
    }
    # Failure sites call exit, so each runs in its own process.
    # The build check and a uv failure both happen before any install attempt.
    'failed-os' {
        Stop-Install "build too old" "unsupported_os"
    }
    'failed-uv' {
        $script:PingArch = "x86_64"
        Stop-Install "uv installation failed: x" "uv_install_failed" "See https://docs.astral.sh/uv/"
    }
    # Both install attempts failed, so extras is still "all".
    'failed-pkg' {
        $script:PingArch = "x86_64"
        $script:InstallExtras = "all"
        Stop-Install "Installation failed." "pkg_install_failed" "Check Python 3.13"
    }
    'failed-path' {
        $script:PingArch = "x86_64"
        $script:InstallExtras = "all"
        Stop-Install "phantom not found on PATH." "not_on_path"
    }
    default { throw "unknown scenario: $Scenario" }
}
