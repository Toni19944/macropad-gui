#requires -Version 5.1
<#
.SYNOPSIS
    Build the self-contained Windows macropad-gui.exe.

.DESCRIPTION
    The single documented build command (FR-007, SC-004). Run from anywhere
    with the dev dependencies installed (`pip install -e .[dev]`):

        ./packaging/build_windows.ps1

    It syncs the version in version_info.txt from pyproject.toml (single source
    of truth, R2), then runs PyInstaller against the committed spec with
    --clean so re-runs always reflect current source (US2 AC-3). The artifact
    lands at dist/macropad-gui.exe. Exits non-zero if PyInstaller fails.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Split-Path -Parent $scriptDir
$specFile  = Join-Path $scriptDir 'macropad_gui.spec'
$pyproject = Join-Path $repoRoot 'pyproject.toml'
$versionInfo = Join-Path $scriptDir 'version_info.txt'

# --- Read the single source-of-truth version from pyproject.toml -----------
$projectVersion = $null
foreach ($line in Get-Content -LiteralPath $pyproject) {
    if ($line -match '^\s*version\s*=\s*"([^"]+)"') {
        $projectVersion = $Matches[1]
        break
    }
}
if (-not $projectVersion) {
    Write-Error "Could not read [project].version from $pyproject"
    exit 1
}
Write-Host "macropad-gui version: $projectVersion"

# --- Sync version strings into the VERSIONINFO resource --------------------
# Build a 4-tuple (major, minor, patch, 0) for the numeric fields.
$parts = @($projectVersion -split '[.+-]') | Where-Object { $_ -match '^\d+$' }
while ($parts.Count -lt 4) { $parts += '0' }
$tuple = '({0}, {1}, {2}, {3})' -f $parts[0], $parts[1], $parts[2], $parts[3]

$vi = Get-Content -LiteralPath $versionInfo -Raw -Encoding UTF8
$vi = [regex]::Replace($vi, 'filevers=\([^)]*\)', "filevers=$tuple")
$vi = [regex]::Replace($vi, 'prodvers=\([^)]*\)', "prodvers=$tuple")
$vi = [regex]::Replace($vi, "StringStruct\('FileVersion', '[^']*'\)", "StringStruct('FileVersion', '$projectVersion')")
$vi = [regex]::Replace($vi, "StringStruct\('ProductVersion', '[^']*'\)", "StringStruct('ProductVersion', '$projectVersion')")
Set-Content -LiteralPath $versionInfo -Value $vi -Encoding UTF8

# --- Build -----------------------------------------------------------------
Push-Location $repoRoot
try {
    & pyinstaller $specFile --noconfirm --clean
    $code = $LASTEXITCODE
} finally {
    Pop-Location
}

if ($code -ne 0) {
    Write-Error "PyInstaller failed (exit $code)."
    exit $code
}

$exe = Join-Path $repoRoot 'dist/macropad-gui.exe'
if (-not (Test-Path -LiteralPath $exe)) {
    Write-Error "Build reported success but $exe was not found."
    exit 1
}
Write-Host "Built: $exe"
