# start-truemath.ps1
# TrueMath ko ek click mein start karne ke liye

# Script ka directory set karein
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Function to kill ALL processes using a specific port (repeats until the
# port is actually free -- Windows can let several stale python.exe instances
# pile up as LISTENERs on the same port, which causes random old/new behavior).
function Kill-Process-On-Port {
    param([int]$Port)
    for ($attempt = 1; $attempt -le 5; $attempt++) {
        $killedAny = $false
        try {
            # Get-NetTCPConnection is far more reliable than parsing netstat text
            $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        } catch {
            $conns = $null
        }
        if (-not $conns) { break }

        $ownerPids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($ownerPid in $ownerPids) {
            Write-Host "Killing process $ownerPid using port $Port..." -ForegroundColor Yellow
            Stop-Process -Id $ownerPid -Force -ErrorAction SilentlyContinue
            $killedAny = $true
        }
        if ($killedAny) { Start-Sleep -Milliseconds 500 }
    }
}

# Belt-and-braces: also kill any leftover TrueMath python.exe processes by
# command line, in case they somehow aren't holding the port anymore but are
# still running (e.g. hung IPC thread).
function Kill-Stale-TrueMath-Python {
    try {
        $procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -match 'main\.py' }
        foreach ($p in $procs) {
            Write-Host "Killing stale TrueMath python process $($p.ProcessId)..." -ForegroundColor Yellow
            Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        }
    } catch {
        # Ignore errors (e.g. no permission to query other processes)
    }
}

# Clean up ports 8080 and 9999
Write-Host "Cleaning up old ports..." -ForegroundColor Magenta
Kill-Stale-TrueMath-Python
Kill-Process-On-Port 8080
Kill-Process-On-Port 9999
Start-Sleep -Seconds 1

# Final verification -- warn loudly if the port is still occupied
$stillBusy = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue
if ($stillBusy) {
    Write-Host "WARNING: Port 8080 abhi bhi busy hai! Koi process ban rahi hogi ya admin rights chahiye." -ForegroundColor Red
    Write-Host "Manually check karein: netstat -ano | findstr :8080" -ForegroundColor Red
}

# Prefer the project's own virtual environment (created by setup-venv.ps1)
# over whatever "python" happens to resolve to globally -- this is what
# actually has sympy/scipy/cryptography/etc. installed.
$repoRoot = $PSScriptRoot
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (Test-Path $venvPython) {
    Write-Host "Using virtual environment: $venvPython" -ForegroundColor Green
    $PythonExe = $venvPython
} else {
    $PythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $PythonCmd) {
        Write-Host "ERROR: Python nahi mil raha! Pehle Python install karein aur PATH mein add karein." -ForegroundColor Red
        Write-Host ""
        Read-Host "Exit karne ke liye Enter press karein"
        exit 1
    }
    Write-Host "WARNING: .venv nahi mila -- global 'python' use ho raha hai. Pehle .\setup-venv.ps1 chalana behtar hai." -ForegroundColor Yellow
    $PythonExe = "python"
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  TrueMath Start Ho Raha Hai..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Ek naya app window khulega (TrueMath)." -ForegroundColor Yellow
Write-Host "Band karne ke liye is window ko close karein, ya terminal mein Ctrl + C." -ForegroundColor Yellow
Write-Host ""

# Server start karein
& $PythonExe main.py
