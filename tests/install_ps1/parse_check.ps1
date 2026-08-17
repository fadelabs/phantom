# Parses install.ps1 without running it. Fails on any syntax error, which is
# the cheapest way to catch a construct that the authoring machine's PowerShell
# accepts but Windows PowerShell 5.1 does not.
param(
    [string]$InstallScript = (Join-Path $PSScriptRoot '../../install.ps1')
)

$resolved = (Resolve-Path $InstallScript).Path
$errors = $null
$tokens = $null
# Decode as UTF-8 explicitly, then parse the string. This is how the script
# actually reaches users: `irm | iex` decodes the response with the charset the
# server sends (GitHub raw sends utf-8) and parses a string. ParseFile would
# instead read the bytes off disk, and Windows PowerShell 5.1 assumes ANSI for a
# file with no byte-order mark, which mangles the script's Unicode glyphs.
$src = [System.IO.File]::ReadAllText($resolved, [System.Text.Encoding]::UTF8)
[System.Management.Automation.Language.Parser]::ParseInput($src, [ref]$tokens, [ref]$errors) | Out-Null

if ($errors) {
    $errors | ForEach-Object {
        Write-Host "PARSE ERROR line $($_.Extent.StartLineNumber): $($_.Message)"
    }
    exit 1
}
Write-Host "install.ps1 parses clean ($($tokens.Count) tokens)"
