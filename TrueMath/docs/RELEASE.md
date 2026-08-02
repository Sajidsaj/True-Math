# Release Guide

## Pre-Release Gates

- `VERSION` updated
- `CHANGELOG.md` updated
- `python -m pytest` passes
- `ui` lint and build pass
- `scripts/sync-version.ps1` has been run
- `dist/TrueMath/TrueMath.exe` launches on a clean Windows machine
- Installer creation succeeds

## Release Commands

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\release.ps1
```

## Output Artifacts

- `dist/TrueMath/` packaged application folder
- `release/TrueMath-Setup.exe` Windows installer
- `release/SHA256SUMS.txt` checksum manifest

## Manual Sign-Off

1. Install on a clean Windows profile
2. Launch the desktop app
3. Verify the version shown in the footer
4. Confirm logs and databases are written under `%LOCALAPPDATA%\TrueMath`
5. Verify uninstall removes the application binaries
6. Verify upgrade preserves the data directory

## Rollback

1. Unpublish the defective installer
2. Reissue the previous stable installer
3. Keep user data in `%LOCALAPPDATA%\TrueMath`
4. Note the rollback in `CHANGELOG.md`
