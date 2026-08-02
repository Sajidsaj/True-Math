from __future__ import annotations

import os
import sys
from pathlib import Path


APP_NAME = "TrueMath"


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def read_version(version_file: Path) -> str:
    try:
        return version_file.read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def get_bundle_root(project_root: Path) -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return project_root


def get_app_home(project_root: Path, app_name: str = APP_NAME) -> Path:
    override = os.getenv("TRUEMATH_APP_HOME")
    if override:
        return Path(override).expanduser().resolve()

    if is_frozen() or os.getenv("TRUEMATH_FORCE_USER_DIR", "0") == "1":
        local_app_data = os.getenv("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data).expanduser().resolve() / app_name
        return Path.home().resolve() / "AppData" / "Local" / app_name

    return project_root
