$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$releaseDir = Join-Path $repoRoot "release"
$checksumFile = Join-Path $releaseDir "SHA256SUMS.txt"

& (Join-Path $PSScriptRoot "package-installer.ps1")

if (-not (Test-Path $releaseDir)) {
    throw "Release directory was not created."
}

if (Test-Path $checksumFile) {
    Remove-Item -Path $checksumFile -Force
}

$artifacts = Get-ChildItem -Path $releaseDir -File
if (-not $artifacts) {
    throw "No release artifacts found."
}

$hashLines = foreach ($artifact in $artifacts) {
    $hash = Get-FileHash -Algorithm SHA256 -Path $artifact.FullName
    "{0} *{1}" -f $hash.Hash.ToLowerInvariant(), $artifact.Name
}

Set-Content -Path $checksumFile -Value $hashLines -Encoding utf8
Write-Host "Release artifacts and checksums created in $releaseDir"
