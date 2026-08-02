# TrueMath Desktop Application

TrueMath is a Windows-first desktop application that packages a Python research
engine, a local React dashboard, and a release pipeline for producing
installable builds.

## What Ships

- Native desktop window powered by `pywebview`
- Python backend orchestrator and localhost IPC services
- React/Vite dashboard bundled into the application image
- PowerShell release scripts for build, packaging, and installer generation
- Inno Setup installer definition for Windows distribution

## Quick Start

### 1. Install backend dependencies

```powershell
python -m pip install -r requirements.txt
```

### 2. Install frontend dependencies

```powershell
cd ui
npm ci
cd ..
```

### 3. Build the desktop UI bundle

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-ui.ps1
```

### 4. Run the desktop app

```powershell
python main.py
```

By default the app opens in a native desktop window. Set
`TRUEMATH_DESKTOP_MODE=false` if you need the legacy browser-hosted workflow.

## Project Layout

```text
.
|-- config.py
|-- main.py
|-- pyproject.toml
|-- requirements.txt
|-- VERSION
|-- scripts/
|   |-- build-ui.ps1
|   |-- build-app.ps1
|   |-- package-installer.ps1
|   |-- release.ps1
|   `-- sync-version.ps1
|-- installer/
|   `-- TrueMath.iss
|-- src/
|   |-- runtime_paths.py
|   |-- core/
|   |-- ai/
|   |-- math_engine/
|   |-- memory/
|   |-- network/
|   `-- ui_bridge/
|-- tests/
|-- ui/
`-- docs/
```

## Configuration

`config.py` is the single runtime settings module. It now supports typed
environment overrides for release deployments.

Common variables:

| Variable | Default | Purpose |
|---|---|---|
| `TRUEMATH_APP_HOME` | `%LOCALAPPDATA%\TrueMath` in packaged builds | Mutable runtime root |
| `TRUEMATH_DASHBOARD_ASSET_DIR` | bundled `ui/dist` | Frontend build location |
| `TRUEMATH_LOG_DIR` | `<app-home>\logs` | Rolling application logs |
| `TRUEMATH_STATE_DB_PATH` | `<app-home>\data\truemath_state.db` | Research state database |
| `TRUEMATH_DESKTOP_MODE` | `true` | Enable native desktop window |
| `TRUEMATH_LLM_BASE_URL` | `http://127.0.0.1:11434/api/generate` | Local LLM endpoint |

See `.env.example` for the full list.

## Build And Release

### Local quality gates

```powershell
python -m pytest
cd ui
npm run lint
npm run build
cd ..
```

### Build a distributable app

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-app.ps1
```

### Build the Windows installer

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\package-installer.ps1
```

### Run the end-to-end release pipeline

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\release.ps1
```

## Operations Docs

- [Install Guide](file:///c:/Users/MRC/OneDrive/Desktop/New%20folder%20(2)/docs/INSTALL.md)
- [Release Guide](file:///c:/Users/MRC/OneDrive/Desktop/New%20folder%20(2)/docs/RELEASE.md)
- [Operations Guide](file:///c:/Users/MRC/OneDrive/Desktop/New%20folder%20(2)/docs/OPERATIONS.md)

## External Requirements

- Python 3.13
- Node.js 20+
- Lean 4 for formal verification
- Ollama for local LLM inference
- Inno Setup 6 for MSI-style installer creation
