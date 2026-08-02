$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$releaseDir = Join-Path $repoRoot "release"
$iscc = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue

if (-not $iscc) {
    throw "Inno Setup compiler (ISCC.exe) not found in PATH."
}

& (Join-Path $PSScriptRoot "build-app.ps1")

if (-not (Test-Path $releaseDir)) {
    New-Item -ItemType Directory -Path $releaseDir | Out-Null
}

Push-Location $repoRoot
try {
    & $iscc.Source (Join-Path $repoRoot "installer\TrueMath.iss")
}
finally {
    Pop-Location
}
