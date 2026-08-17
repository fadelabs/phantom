# Runs install.ps1 the way `irm <url> | iex` does: decode the script as UTF-8
# (the charset GitHub raw serves), then Invoke-Expression the resulting string.
#
# This exists as a file rather than an inline -Command string so the paths never
# have to survive Start-Process argument quoting.
param(
    [string]$InstallScript = (Join-Path $PSScriptRoot '../../install.ps1')
)

$resolved = (Resolve-Path $InstallScript).Path
$src = [System.IO.File]::ReadAllText($resolved, [System.Text.Encoding]::UTF8)
Invoke-Expression $src
