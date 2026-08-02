# setup-lean4.ps1
# ------------------------------------------------------------------
# ONE-TIME, OPTIONAL setup for full Lean 4 + Mathlib formal verification.
#
# Without this script, TrueMath still formally checks pure-integer
# expressions (e.g. x^2 + y*z) using bare Lean 4 once it's installed.
# This script additionally enables checking of expressions with
# trig/exp/log/pi (which need Mathlib's real-number library).
#
# WARNING: This is a HEAVY one-time operation:
#   - Downloads elan (Lean's version manager) if not already installed.
#   - Creates a Lake project and adds Mathlib as a dependency.
#   - Downloads Mathlib's prebuilt cache (a few GB) and builds it.
#   - Can take 15-60 minutes depending on your internet connection.
#
# Run this manually once:  .\scripts\setup-lean4.ps1
# ------------------------------------------------------------------
$ErrorActionPreference = "Stop"

$repoRoot   = Split-Path -Parent $PSScriptRoot
$projectDir = Join-Path $repoRoot "lean4_project"

Write-Host "=== TrueMath: Lean 4 + Mathlib setup ===" -ForegroundColor Magenta

# 1) Install elan (Lean's toolchain manager) if `lean`/`lake` aren't present.
$leanCmd = Get-Command lean -ErrorAction SilentlyContinue
$lakeCmd = Get-Command lake -ErrorAction SilentlyContinue

if (-not $leanCmd -or -not $lakeCmd) {
    Write-Host "Lean 4 not found -- installing elan..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri "https://raw.githubusercontent.com/leanprover/elan/master/elan-init.ps1" -OutFile "$env:TEMP\elan-init.ps1"
    & "$env:TEMP\elan-init.ps1" -NoPrompt
    $env:Path += ";$env:USERPROFILE\.elan\bin"
    Write-Host "elan installed. You may need to restart your terminal for PATH changes to fully apply." -ForegroundColor Yellow
} else {
    Write-Host "Lean 4 / Lake already found on PATH." -ForegroundColor Green
}

# 2) Create a minimal Lake project with Mathlib as a dependency, if it
#    doesn't already exist.
if (-not (Test-Path $projectDir)) {
    Write-Host "Creating Lake project at $projectDir ..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $projectDir | Out-Null
    Push-Location $projectDir
    try {
        lake init truemath_lean math
    } finally {
        Pop-Location
    }
}

Push-Location $projectDir
try {
    $lakefile = Join-Path $projectDir "lakefile.lean"
    $content = Get-Content $lakefile -Raw -ErrorAction SilentlyContinue
    if ($content -notmatch "Mathlib") {
        Write-Host "Adding Mathlib dependency to lakefile.lean..." -ForegroundColor Yellow
        Add-Content $lakefile "`nrequire mathlib from git `"https://github.com/leanprover-community/mathlib4.git`""
    }

    Write-Host "Fetching dependencies (this downloads Mathlib -- can take a while)..." -ForegroundColor Yellow
    lake update

    Write-Host "Building Mathlib (heavy step -- 15-60 minutes, few GB disk)..." -ForegroundColor Yellow
    lake build

} finally {
    Pop-Location
}

Write-Host "`n=== Done! ===" -ForegroundColor Green
Write-Host "Add this line to your .env file to enable it:" -ForegroundColor Cyan
Write-Host "TRUEMATH_LEAN4_PROJECT_DIR=$projectDir" -ForegroundColor White
Write-Host "Then restart TrueMath. Pure-integer checks already work without this." -ForegroundColor Cyan
