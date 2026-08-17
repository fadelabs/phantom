# Phantom installer for Windows
# irm https://raw.githubusercontent.com/fadelabs/phantom/main/install.ps1 | iex
# Or from cmd.exe:
# powershell -NoProfile -c "irm https://raw.githubusercontent.com/fadelabs/phantom/main/install.ps1 | iex"

$ErrorActionPreference = "Stop"

# TLS 1.2 (required for PS 5.1 on older Windows 10)
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Write-Ok    { param([string]$msg) Write-Host "  ✓ $msg" -ForegroundColor Green }
function Write-Fail  { param([string]$msg) Write-Host "  ✗ $msg" -ForegroundColor Red }
function Write-Info  { param([string]$msg) Write-Host "  ▸ $msg" -ForegroundColor Cyan }
function Write-Warn  { param([string]$msg) Write-Host "  ! $msg" -ForegroundColor Yellow }

# Values are reduced to a safe charset so they stay predictable in reporting.
function ConvertTo-SafeValue {
    param([string]$value)
    return ($value -replace '[^A-Za-z0-9._,+-]', '')
}

function Send-Ping {
    # Fire-and-forget install telemetry. Never fails the install, never blocks.
    # Mirrors install.sh: POST + JSON to the same endpoint, same three events,
    # same per-run iid so start/complete/failed can be joined server-side.
    # $reason is sent only with install_failed. Full enumerated set (keep in sync
    # with install.sh and fadelab.net reporting): unsupported_os,
    # unsupported_arch, no_downloader, uv_install_failed, pkg_install_failed,
    # not_on_path. unsupported_arch and no_downloader never fire here — this
    # script rejects no architecture and needs no external downloader.
    param([string]$event, [string]$version = "unknown", [string]$reason = "")
    if ($env:PHANTOM_NO_TELEMETRY -eq "1") { return }
    try {
        $safeVersion = ConvertTo-SafeValue $version
        if (-not $safeVersion) { $safeVersion = "unknown" }
        $safeExtras = ConvertTo-SafeValue $script:InstallExtras
        if (-not $safeExtras) { $safeExtras = "none" }

        $body = [ordered]@{
            event   = $event
            iid     = $script:InstallId
            os      = $script:PingOs
            arch    = $script:PingArch
            version = $safeVersion
            extras  = $safeExtras
            method  = "uv"
        }
        if ($reason) { $body.reason = ConvertTo-SafeValue $reason }

        # Synchronous with a short timeout, deliberately. Start-Job would be
        # backgrounded like install.sh's `curl &`, but the failure-path pings are
        # immediately followed by `exit 1`, which kills a pending job before it
        # runs. A blocking call with a 3s cap is the reliable choice here.
        Invoke-WebRequest -Uri "https://fadelab.net/api/ping" -Method Post `
            -ContentType "application/json" -Body ($body | ConvertTo-Json -Compress) `
            -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop | Out-Null
    } catch { }
}

function Stop-Install {
    # Mirrors install.sh's err(): report, send install_failed with an enumerated
    # reason code, then exit.
    param([string]$msg, [string]$reason, [string]$hint = "")
    Write-Fail $msg
    if ($hint) { Write-Host "    $hint" -ForegroundColor DarkGray }
    Send-Ping "install_failed" "" $reason
    exit 1
}

function Publish-EnvironmentChange {
    if (-not ('Win32.NativeMethods' -as [type])) {
        Add-Type -Namespace Win32 -Name NativeMethods -MemberDefinition @'
[DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
public static extern IntPtr SendMessageTimeout(
    IntPtr hWnd, uint Msg, UIntPtr wParam, string lParam,
    uint fuFlags, uint uTimeout, out UIntPtr lpdwResult);
'@
    }
    $HWND_BROADCAST = [IntPtr]0xffff
    $WM_SETTINGCHANGE = 0x1a
    $result = [UIntPtr]::Zero
    [Win32.NativeMethods]::SendMessageTimeout(
        $HWND_BROADCAST, $WM_SETTINGCHANGE, [UIntPtr]::Zero,
        'Environment', 2, 5000, [ref]$result) | Out-Null
}

function Refresh-Path {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")
}

function Add-ToUserPath {
    param([string]$Dir)
    $regKey = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Environment', $true)
    $currentPath = $regKey.GetValue('Path', '', [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)

    if (($currentPath -split ';') -notcontains $Dir) {
        $newPath = "$Dir;$currentPath"
        $kind = if ($newPath.Contains('%')) {
            [Microsoft.Win32.RegistryValueKind]::ExpandString
        } else {
            [Microsoft.Win32.RegistryValueKind]::String
        }
        $regKey.SetValue('Path', $newPath, $kind)
        Publish-EnvironmentChange
    }
    $regKey.Close()
    $env:Path = "$Dir;$env:Path"
}

function Main {
    Write-Host ""
    Write-Host "  Phantom" -NoNewline -ForegroundColor White
    Write-Host " — AI Audio Engineering" -ForegroundColor DarkGray
    Write-Host ""

    # ── Telemetry (opt-out via PHANTOM_NO_TELEMETRY=1) ─────
    # Initialized above the first failure point so an unsupported-Windows exit
    # still reports. Stable per-run id joins the events of a single install.
    # extras stays "none" until an install is actually attempted, so a failure
    # before that point reports the same value install.sh would.
    $script:InstallId = [guid]::NewGuid().ToString()
    $script:InstallExtras = "none"
    $script:PingOs = "windows"
    $script:PingArch = "unknown"

    # ── Windows version check ───────────────────────────────
    $build = [System.Environment]::OSVersion.Version.Build
    if ($build -lt 17763) {
        Stop-Install "Windows 10 version 1809 or later required (build 17763+). You have build $build." "unsupported_os"
    }

    $arch = if ([System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture) {
        [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture
    } else {
        if ([System.Environment]::Is64BitOperatingSystem) { "X64" } else { "X86" }
    }
    Write-Ok "Detected Windows $arch (build $build)"

    # Normalize to install.sh's labels so both installers share one arch axis.
    $script:PingArch = switch ("$arch") {
        "X64"   { "x86_64" }
        "Amd64" { "x86_64" }
        "Arm64" { "arm64" }
        default { ConvertTo-SafeValue ("$arch".ToLower()) }
    }
    Send-Ping "install_started"

    # ── Check/install uv ────────────────────────────────────
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        $uvVersion = (uv --version 2>$null | Select-Object -First 1)
        Write-Ok "uv $uvVersion"
    } else {
        Write-Info "Installing uv..."
        try {
            irm https://astral.sh/uv/install.ps1 | iex
            Refresh-Path
            if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
                throw "uv not found after install"
            }
            Write-Ok "uv installed"
        } catch {
            Stop-Install "uv installation failed: $_" "uv_install_failed" "See https://docs.astral.sh/uv/"
        }
    }

    # ── Install phantom ─────────────────────────────────────
    if (Get-Command phantom -ErrorAction SilentlyContinue) {
        $existing = (phantom --version 2>$null | Select-Object -First 1)
        Write-Warn "Existing install found: $existing — upgrading"
    }

    Write-Info "Installing phantom (this may take a minute)..."
    $uvPath = (Get-Command uv).Source
    $script:InstallExtras = "all"
    $installLog = & $uvPath tool install "phantom-audio[all]" --python 3.13 --force 2>&1 | Out-String
    if ($LASTEXITCODE -eq 0 -or $installLog -match 'Installed.*executable') {
        Write-Ok "Phantom installed"
    } else {
        Write-Warn "Full install failed, trying core only..."
        $installLog = & $uvPath tool install phantom-audio --python 3.13 --force 2>&1 | Out-String
        if ($LASTEXITCODE -eq 0 -or $installLog -match 'Installed.*executable') {
            $script:InstallExtras = "none"
            Write-Ok "Phantom core installed (extras skipped)"
        } else {
            Stop-Install "Installation failed." "pkg_install_failed" "Check Python 3.13: uv python list | Select-String 3.13"
        }
    }

    # ── Verify ──────────────────────────────────────────────
    Refresh-Path
    $uvToolBin = "$env:USERPROFILE\.local\bin"
    if (-not (Get-Command phantom -ErrorAction SilentlyContinue)) {
        Add-ToUserPath $uvToolBin
        if (-not (Get-Command phantom -ErrorAction SilentlyContinue)) {
            Stop-Install "phantom not found on PATH. Add $uvToolBin to your PATH." "not_on_path"
        }
    }

    # `phantom --version` prints "phantom, version X.Y.Z" — report the bare
    # version so it matches what install.sh sends.
    $versionRaw = (phantom --version 2>$null | Select-Object -First 1)
    $version = if ("$versionRaw" -match '\d+\.\d+\.\d+[\w.+-]*') { $Matches[0] } else { "unknown" }
    Write-Ok "Phantom $version"
    Send-Ping "install_complete" $version

    # ── Configure ───────────────────────────────────────────
    Write-Host ""
    Write-Host "  Configuring" -ForegroundColor White
    Write-Host ""

    # MCP server (run from user home to avoid project-local .mcp.json)
    try {
        Push-Location $env:USERPROFILE
        $setupOut = phantom setup --skip-plugin --skip-reaper 2>&1 |
            Where-Object { $_ -notmatch 'DeprecationWarning|AuthlibDeprecation|scipy\.ndimage|from authlib|from scipy|It will be compatible|__main__|cannot be directly' } |
            Out-String
        Pop-Location
        Write-Ok "MCP server"
    } catch {
        Pop-Location
        Write-Warn "MCP setup had issues — run 'phantom setup' to retry"
    }

    # Reaper bridge
    $reaperScripts = "$env:APPDATA\REAPER\Scripts"
    if (Test-Path $reaperScripts) {
        try {
            $null = phantom setup-reaper 2>&1 |
                Where-Object { $_ -notmatch 'DeprecationWarning|AuthlibDeprecation|scipy\.ndimage|from authlib|from scipy|It will be compatible' }
            Write-Ok "Reaper bridge"
        } catch {
            Write-Warn "Reaper setup had issues — run 'phantom setup-reaper' to retry"
        }
    } else {
        Write-Info "Reaper not detected — skipping bridge"
    }

    # Claude Code plugin
    if (Get-Command claude -ErrorAction SilentlyContinue) {
        try {
            claude plugin marketplace add https://github.com/fadelabs/phantom.git 2>$null | Out-Null
            $pluginOut = claude plugin install phantom 2>&1 | Out-String
            if ($LASTEXITCODE -eq 0 -or $pluginOut -match 'installed|already') {
                Write-Ok "Claude Code plugin"
            } else {
                Write-Warn "Plugin install failed — run: claude plugin install phantom"
            }
        } catch {
            Write-Warn "Plugin install failed — run: claude plugin install phantom"
        }
    } else {
        Write-Info "Claude Code not found — install from https://claude.ai/code"
    }

    # ── Success ─────────────────────────────────────────────
    Write-Host ""
    Write-Host "  Phantom is ready." -ForegroundColor Green
    Write-Host ""
    Write-Host "  Get started:" -ForegroundColor DarkGray
    Write-Host "    phantom analyze your-track.wav" -ForegroundColor Cyan
    Write-Host "    phantom --help" -ForegroundColor Cyan
    Write-Host ""
}

Main
