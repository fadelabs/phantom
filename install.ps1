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

    # ── Windows version check ───────────────────────────────
    $build = [System.Environment]::OSVersion.Version.Build
    if ($build -lt 17763) {
        Write-Fail "Windows 10 version 1809 or later required (build 17763+). You have build $build."
        exit 1
    }

    $arch = if ([System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture) {
        [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture
    } else {
        if ([System.Environment]::Is64BitOperatingSystem) { "X64" } else { "X86" }
    }
    Write-Ok "Detected Windows $arch (build $build)"

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
            Write-Fail "uv installation failed: $_"
            Write-Host "    See https://docs.astral.sh/uv/" -ForegroundColor DarkGray
            exit 1
        }
    }

    # ── Install phantom ─────────────────────────────────────
    if (Get-Command phantom -ErrorAction SilentlyContinue) {
        $existing = (phantom --version 2>$null | Select-Object -First 1)
        Write-Warn "Existing install found: $existing — upgrading"
    }

    Write-Info "Installing phantom (this may take a minute)..."
    $uvPath = (Get-Command uv).Source
    $installLog = & $uvPath tool install "phantom-audio[all]" --python 3.13 --force 2>&1 | Out-String
    if ($LASTEXITCODE -eq 0 -or $installLog -match 'Installed.*executable') {
        Write-Ok "Phantom installed"
    } else {
        Write-Warn "Full install failed, trying core only..."
        $installLog = & $uvPath tool install phantom-audio --python 3.13 --force 2>&1 | Out-String
        if ($LASTEXITCODE -eq 0 -or $installLog -match 'Installed.*executable') {
            Write-Ok "Phantom core installed (extras skipped)"
        } else {
            Write-Fail "Installation failed."
            Write-Host "    Check Python 3.13: uv python list | Select-String 3.13" -ForegroundColor DarkGray
            exit 1
        }
    }

    # ── Verify ──────────────────────────────────────────────
    Refresh-Path
    $uvToolBin = "$env:USERPROFILE\.local\bin"
    if (-not (Get-Command phantom -ErrorAction SilentlyContinue)) {
        Add-ToUserPath $uvToolBin
        if (-not (Get-Command phantom -ErrorAction SilentlyContinue)) {
            Write-Fail "phantom not found on PATH. Add $uvToolBin to your PATH."
            exit 1
        }
    }

    $version = (phantom --version 2>$null | Select-Object -First 1)
    Write-Ok "Phantom $version"

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
