$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$version = (Get-Content -Path (Join-Path $repoRoot "VERSION") -Raw).Trim()
$regexOptions = [System.Text.RegularExpressions.RegexOptions]::Multiline

function Set-FileContentUtf8NoBom {
    param(
        [string]$Path,
        [string]$Content
    )

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

$packageJsonPath = Join-Path $repoRoot "ui\package.json"
$packageJson = Get-Content -Path $packageJsonPath -Raw
$packageJson = ([regex]::new('^(\s*"name":\s*")(.+)(")$', $regexOptions)).Replace($packageJson, '$1truemath-ui$3', 1)
$packageJson = ([regex]::new('^(\s*"version":\s*")(.+)(")$', $regexOptions)).Replace($packageJson, "`$1$version`$3", 1)
Set-FileContentUtf8NoBom -Path $packageJsonPath -Content $packageJson

$packageLockPath = Join-Path $repoRoot "ui\package-lock.json"
$packageLock = Get-Content -Path $packageLockPath -Raw
$packageLock = ([regex]::new('^(\s*"name":\s*")(.+)(")$', $regexOptions)).Replace($packageLock, '$1truemath-ui$3', 2)
$packageLock = ([regex]::new('^(\s*"version":\s*")(.+)(")$', $regexOptions)).Replace($packageLock, "`$1$version`$3", 2)
Set-FileContentUtf8NoBom -Path $packageLockPath -Content $packageLock

$versionJsPath = Join-Path $repoRoot "ui\src\version.js"
Set-FileContentUtf8NoBom -Path $versionJsPath -Content "export const APP_VERSION = '$version'`n"

$pyprojectPath = Join-Path $repoRoot "pyproject.toml"
$pyproject = Get-Content -Path $pyprojectPath -Raw
$pyproject = [System.Text.RegularExpressions.Regex]::Replace(
    $pyproject,
    '(?m)^version = ".*"$',
    "version = `"$version`""
)
Set-FileContentUtf8NoBom -Path $pyprojectPath -Content $pyproject

$installerPath = Join-Path $repoRoot "installer\TrueMath.iss"
$installer = Get-Content -Path $installerPath -Raw
$installer = [System.Text.RegularExpressions.Regex]::Replace(
    $installer,
    '(?m)^#define MyAppVersion ".*"$',
    "#define MyAppVersion `"$version`""
)
Set-FileContentUtf8NoBom -Path $installerPath -Content $installer

Write-Host "Synchronized version $version"
