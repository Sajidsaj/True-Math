$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

& (Join-Path $PSScriptRoot "sync-version.ps1")

Push-Location (Join-Path $repoRoot "ui")
try {
    npm ci
    npm run lint
    npm run build
}
finally {
    Pop-Location
}
