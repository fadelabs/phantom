# Evaluates the two inline expressions in install.ps1 (arch normalization and
# version parsing) by lifting them out of the shipped source, so these checks
# cannot drift from the code they cover. Prints "EXPR|<label>|<value>".
param(
    [string]$InstallScript = (Join-Path $PSScriptRoot '../../install.ps1')
)

# UTF-8 explicitly; see the note in scenario.ps1.
$src = [System.IO.File]::ReadAllText((Resolve-Path $InstallScript).Path, [System.Text.Encoding]::UTF8)
$src2 = $src -replace '(?m)^Main\s*$', '' -replace '(?m)^\[Net\.ServicePointManager\].*$', ''
Invoke-Expression $src2

$archBlock = [regex]::Match($src, '(?ms)^\s*\$script:PingArch = switch \("\$arch"\) \{.*?^    \}').Value
if (-not $archBlock) { Write-Host "EXPR|arch-block-found|NO"; exit 1 }
Write-Host "EXPR|arch-block-found|YES"
foreach ($a in @('X64', 'Amd64', 'Arm64', 'X86')) {
    $arch = $a
    Invoke-Expression $archBlock
    Write-Host "EXPR|arch:$a|$script:PingArch"
}

$verExpr = [regex]::Match($src, '(?m)^\s*\$version = if \("\$versionRaw".*$').Value
if (-not $verExpr) { Write-Host "EXPR|version-expr-found|NO"; exit 1 }
Write-Host "EXPR|version-expr-found|YES"
foreach ($v in @('phantom, version 1.5.0', 'phantom, version 1.5.0rc1', '', 'garbage output')) {
    $versionRaw = $v
    Invoke-Expression $verExpr
    Write-Host "EXPR|version:$v|$version"
}
