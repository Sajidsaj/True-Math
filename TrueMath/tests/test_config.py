from __future__ import annotations

from pathlib import Path

import pytest

import config


def test_ensure_runtime_dirs_creates_data_and_log_roots(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr(config, "STATE_DB_PATH", str(tmp_path / "data" / "state.db"))
    monkeypatch.setattr(config, "GRAVEYARD_DB_PATH", str(tmp_path / "data" / "graveyard.db"))

    config.ensure_runtime_dirs()

    assert (tmp_path / "logs").exists()
    assert (tmp_path / "data").exists()


def test_validate_runtime_rejects_missing_dashboard_build(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DASHBOARD_ASSET_DIR", str(tmp_path / "missing-dist"))

    with pytest.raises(RuntimeError):
        config.validate_runtime()


def test_validate_runtime_accepts_index_html(monkeypatch, tmp_path):
    asset_dir = tmp_path / "dist"
    asset_dir.mkdir()
    (asset_dir / "index.html").write_text("<html></html>", encoding="utf-8")
    monkeypatch.setattr(config, "DASHBOARD_ASSET_DIR", str(asset_dir))

    config.validate_runtime()


def test_validate_runtime_rejects_non_loopback_hosts(monkeypatch, tmp_path):
    asset_dir = tmp_path / "dist"
    asset_dir.mkdir()
    (asset_dir / "index.html").write_text("<html></html>", encoding="utf-8")
    monkeypatch.setattr(config, "DASHBOARD_ASSET_DIR", str(asset_dir))
    monkeypatch.setattr(config, "IPC_HOST", "0.0.0.0")

    with pytest.raises(RuntimeError, match="loopback"):
        config.validate_runtime()


def test_validate_runtime_rejects_invalid_ports(monkeypatch, tmp_path):
    asset_dir = tmp_path / "dist"
    asset_dir.mkdir()
    (asset_dir / "index.html").write_text("<html></html>", encoding="utf-8")
    monkeypatch.setattr(config, "DASHBOARD_ASSET_DIR", str(asset_dir))
    monkeypatch.setattr(config, "IPC_PORT", 70000)

    with pytest.raises(RuntimeError, match="between 1 and 65535"):
        config.validate_runtime()


def test_version_loaded_from_root_version_file():
    version_file = Path(config.PROJECT_ROOT) / "VERSION"
    assert config.APP_VERSION == version_file.read_text(encoding="utf-8").strip()
