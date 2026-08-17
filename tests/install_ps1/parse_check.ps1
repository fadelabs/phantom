# Parses install.ps1 without running it. Fails on any syntax error, which is
# the cheapest way to catch a construct that the authoring machine's PowerShell
# accepts but Windows PowerShell 5.1 does not.
param(
    [string]$InstallScript = (Join-Path $PSScriptRoot '../../install.ps1')
)

$resolved = (Resolve-Path $InstallScript).Path
$errors = $null
$tokens = $null
[System.Management.Automation.Language.Parser]::ParseFile($resolved, [ref]$tokens, [ref]$errors) | Out-Null

if ($errors) {
    $errors | ForEach-Object {
        Write-Host "PARSE ERROR line $($_.Extent.StartLineNumber): $($_.Message)"
    }
    exit 1
}
Write-Host "install.ps1 parses clean ($($tokens.Count) tokens)"
