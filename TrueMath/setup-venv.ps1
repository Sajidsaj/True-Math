# TrueMath Virtual Environment Setup Script (Windows PowerShell)
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  TrueMath Virtual Environment Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is available
Write-Host "Checking for Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python not found in PATH! Please install Python 3.13+ and add it to PATH." -ForegroundColor Red
    exit 1
}

# Create virtual environment if it doesn't exist
$venvPath = ".venv"
if (-not (Test-Path $venvPath)) {
    Write-Host ""
    Write-Host "Creating virtual environment at $venvPath..." -ForegroundColor Yellow
    python -m venv $venvPath
    Write-Host "Virtual environment created successfully!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Virtual environment already exists at $venvPath" -ForegroundColor Cyan
}

# Activate and install dependencies
Write-Host ""
Write-Host "Activating virtual environment and installing dependencies..." -ForegroundColor Yellow
& $venvPath\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "To activate the virtual environment, run:" -ForegroundColor Cyan
Write-Host "  .\activate-venv.ps1" -ForegroundColor White
Write-Host ""
