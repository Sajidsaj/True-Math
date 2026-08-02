$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$distDir = Join-Path $repoRoot "dist"
$buildDir = Join-Path $repoRoot "build"

& (Join-Path $PSScriptRoot "build-ui.ps1")

Push-Location $repoRoot
try {
    python -m pytest

    if (Test-Path $distDir) {
        Remove-Item -Recurse -Force $distDir
    }

    if (Test-Path $buildDir) {
        Remove-Item -Recurse -Force $buildDir
    }

    pyinstaller `
        --noconfirm `
        --clean `
        TrueMath.spec
}
finally {
    Pop-Location
}
