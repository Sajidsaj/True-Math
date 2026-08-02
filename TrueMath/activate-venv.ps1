# TrueMath Virtual Environment Activation Script (Windows PowerShell)
$venvPath = ".venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "ERROR: Virtual environment not found at $venvPath!" -ForegroundColor Red
    Write-Host "Please run setup-venv.ps1 first." -ForegroundColor Yellow
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Activating TrueMath Virtual Environment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Activate the virtual environment
& $venvPath\Scripts\Activate.ps1
