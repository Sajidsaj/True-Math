# Install Guide

## Prerequisites

- Python 3.13
- Node.js 20 or newer
- Ollama if local inference is required
- Lean 4 if formal proof checks are required
- Inno Setup 6 if you are producing the installer yourself

## Developer Install

```powershell
python -m pip install -r requirements.txt
cd ui
npm ci
cd ..
powershell -ExecutionPolicy Bypass -File .\scripts\build-ui.ps1
python main.py
```

## Packaged Install

1. Run `TrueMath-Setup.exe`
2. Accept the install directory
3. Launch `TrueMath` from the Start Menu or Desktop shortcut
4. Review `%LOCALAPPDATA%\TrueMath\logs\truemath_system.log` if startup fails

## Uninstall

1. Open Windows `Apps > Installed Apps`
2. Select `TrueMath`
3. Choose `Uninstall`
4. Remove `%LOCALAPPDATA%\TrueMath` manually only if you want to delete user data
