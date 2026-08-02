# create-desktop-shortcut.ps1
# ------------------------------------------------------------------
# Creates a real Windows Desktop shortcut (TrueMath.lnk) that launches
# TrueMath with NO visible terminal window -- just the app window.
#
# Run once:  .\create-desktop-shortcut.ps1
# ------------------------------------------------------------------
$ErrorActionPreference = "Stop"

$repoRoot   = $PSScriptRoot
$vbsPath    = Join-Path $repoRoot "start-truemath-hidden.vbs"
$desktopDir = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktopDir "TrueMath.lnk"

if (-not (Test-Path $vbsPath)) {
    Write-Host "ERROR: start-truemath-hidden.vbs not found at $vbsPath" -ForegroundColor Red
    exit 1
}

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($shortcutPath)
$Shortcut.TargetPath = $vbsPath
$Shortcut.WorkingDirectory = $repoRoot
$Shortcut.Description = "TrueMath -- Math Research & Problem Solver"

# Use a built-in Windows icon (calculator-like) if no custom .ico is bundled.
$iconPath = Join-Path $repoRoot "ui\public\favicon.ico"
if (Test-Path $iconPath) {
    $Shortcut.IconLocation = $iconPath
} else {
    $Shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,15"  # calculator-ish icon
}

$Shortcut.Save()

Write-Host "Desktop shortcut banaya gaya: $shortcutPath" -ForegroundColor Green
Write-Host "Ab Desktop pe 'TrueMath' icon pe double-click karke app chala sakte ho -- koi terminal nahi dikhega." -ForegroundColor Cyan
