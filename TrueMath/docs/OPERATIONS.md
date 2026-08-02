# Operations Guide

## Runtime Directories

- Logs: `%LOCALAPPDATA%\TrueMath\logs`
- Databases: `%LOCALAPPDATA%\TrueMath\data`
- Frontend assets: packaged under the install directory

Development mode uses the repository root unless `TRUEMATH_APP_HOME` is set.

## Health Checks

- Dashboard HTTP endpoint: `http://127.0.0.1:8080`
- IPC WebSocket: `ws://127.0.0.1:9999`
- Main log file: `truemath_system.log`

## Common Overrides

```powershell
$env:TRUEMATH_DESKTOP_MODE="false"
$env:TRUEMATH_LLM_MODEL_NAME="llama3:latest"
$env:TRUEMATH_APP_HOME="$env:LOCALAPPDATA\TrueMath-Staging"
python main.py
```

## Failure Triage

1. Confirm `ui/dist/index.html` exists
2. Check if ports `8080` and `9999` are already in use
3. Check Ollama availability if inference requests are failing
4. Check Lean 4 availability if proof verification is expected
5. Review the rotating log files under the app log directory
