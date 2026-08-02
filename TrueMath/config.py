"""
Application configuration and runtime path resolution.

The release build resolves mutable application data into the user's profile
directory while development builds continue to work from the repository root.
All values can be overridden via TRUEMATH_* environment variables.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, TypeVar

from dotenv import load_dotenv

from src.runtime_paths import APP_NAME, get_app_home, get_bundle_root, get_project_root, read_version

# CRITICAL: this actually reads the .env file and injects its values into
# os.environ. Without this call, every TRUEMATH_* setting in .env (API
# keys included) was silently ignored — os.environ.get() never sees .env
# file contents unless something explicitly loads it first. This was a
# real, serious bug: setup-api-keys.ps1 correctly wrote keys to .env, but
# nothing ever read that file back in, so the keys were never actually used.
load_dotenv(get_project_root() / ".env")


PROJECT_ROOT: Path = get_project_root()
BUNDLE_ROOT: Path = get_bundle_root(PROJECT_ROOT)
APP_VERSION: str = read_version(PROJECT_ROOT / "VERSION")
APP_HOME: Path = get_app_home(PROJECT_ROOT, APP_NAME)
DATA_DIR: Path = APP_HOME / "data"
LOG_PATH_ROOT: Path = APP_HOME / "logs"

T = TypeVar("T")


def _env_value(name: str, default: T, parser: Callable[[str], T]) -> T:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return parser(raw.strip())
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"Invalid value for {name}: {raw}") from exc


def _env_bool(name: str, default: bool) -> bool:
    def _parse(raw: str) -> bool:
        normalized = raw.lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        raise ValueError(raw)

    return _env_value(name, default, _parse)


def _env_int(name: str, default: int) -> int:
    return _env_value(name, default, int)


def _env_float(name: str, default: float) -> float:
    return _env_value(name, default, float)


def _env_path(name: str, default: Path) -> Path:
    return Path(_env_value(name, str(default), str)).expanduser().resolve()


def _is_loopback_host(host: str) -> bool:
    normalized = host.strip().lower()
    return normalized in {"127.0.0.1", "localhost", "::1"}


def _is_valid_port(port: int) -> bool:
    return 1 <= port <= 65535


# ── Logging ──────────────────────────────────────────────────
LOG_DIR: str = str(_env_path("TRUEMATH_LOG_DIR", LOG_PATH_ROOT))

# ── Database Paths ───────────────────────────────────────────
STATE_DB_PATH: str = str(_env_path("TRUEMATH_STATE_DB_PATH", DATA_DIR / "truemath_state.db"))
HISTORY_DB_PATH: str = str(_env_path("TRUEMATH_HISTORY_DB_PATH", DATA_DIR / "truemath_history.db"))
EXPORTS_DIR: str = str(_env_path("TRUEMATH_EXPORTS_DIR", DATA_DIR / "exports"))
GRAVEYARD_DB_PATH: str = str(_env_path("TRUEMATH_GRAVEYARD_DB_PATH", DATA_DIR / "truemath_graveyard.db"))

# ── Cloud LLM Providers (Groq primary, OpenRouter fallback) ───
# API keys are read from environment (.env file) — put your own keys there,
# never hardcode them in source. Runs entirely in the cloud: no local RAM/CPU
# load, so it won't hang your PC the way a local model can.
GROQ_API_KEY: str = _env_value("TRUEMATH_GROQ_API_KEY", "", str)
GROQ_MODEL_NAME: str = _env_value("TRUEMATH_GROQ_MODEL_NAME", "openai/gpt-oss-120b", str)
GROQ_BASE_URL: str = _env_value("TRUEMATH_GROQ_BASE_URL", "https://api.groq.com/openai/v1/chat/completions", str)

OPENROUTER_API_KEY: str = _env_value("TRUEMATH_OPENROUTER_API_KEY", "", str)
OPENROUTER_MODEL_NAME: str = _env_value("TRUEMATH_OPENROUTER_MODEL_NAME", "deepseek/deepseek-chat", str)
OPENROUTER_BASE_URL: str = _env_value("TRUEMATH_OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1/chat/completions", str)

LLM_TIMEOUT_S: int = _env_int("TRUEMATH_LLM_TIMEOUT_S", 20)

# ── IPC Bridge (Python ↔ React WebSocket) ───────────────────
IPC_HOST: str = _env_value("TRUEMATH_IPC_HOST", "127.0.0.1", str)
IPC_PORT: int = _env_int("TRUEMATH_IPC_PORT", 9999)

# ── Dashboard HTTP Server ────────────────────────────────────
DASHBOARD_HOST: str = _env_value("TRUEMATH_DASHBOARD_HOST", "127.0.0.1", str)
DASHBOARD_PORT: int = _env_int("TRUEMATH_DASHBOARD_PORT", 8080)
DASHBOARD_ASSET_DIR: str = str(
    _env_path("TRUEMATH_DASHBOARD_ASSET_DIR", BUNDLE_ROOT / "ui" / "dist")
)

# ── Desktop Shell ────────────────────────────────────────────
DESKTOP_MODE: bool = _env_bool("TRUEMATH_DESKTOP_MODE", True)
DESKTOP_WIDTH: int = _env_int("TRUEMATH_DESKTOP_WIDTH", 1440)
DESKTOP_HEIGHT: int = _env_int("TRUEMATH_DESKTOP_HEIGHT", 920)
DESKTOP_DEBUG: bool = _env_bool("TRUEMATH_DESKTOP_DEBUG", False)
BROWSER_AUTO_OPEN: bool = _env_bool("TRUEMATH_BROWSER_AUTO_OPEN", True)
AUTO_EXIT_AFTER_SECONDS: int = _env_int("TRUEMATH_AUTO_EXIT_AFTER_SECONDS", 0)

# ── Lean 4 Verification ──────────────────────────────────────
LEAN4_TIMEOUT_S: int = _env_int("TRUEMATH_LEAN4_TIMEOUT_S", 30)
# Path to a built Lake project with Mathlib as a dependency (see
# scripts/setup-lean4.ps1). Optional — without it, trig/exp/log/pi
# expressions simply skip formal verification; pure-integer expressions
# still work with bare Lean 4 and need no project at all.
LEAN4_PROJECT_DIR: str = _env_value("TRUEMATH_LEAN4_PROJECT_DIR", "", str)

# ── MCTS Engine ──────────────────────────────────────────────
MCTS_EXPLORATION_WEIGHT: float = _env_float("TRUEMATH_MCTS_EXPLORATION_WEIGHT", 1.41)

# ── Falsification Engine ─────────────────────────────────────
FALSIFICATION_ITERATIONS: int = _env_int("TRUEMATH_FALSIFICATION_ITERATIONS", 1000)

# ── Symbolic Genesis ─────────────────────────────────────────
GENESIS_PATTERN_THRESHOLD: int = _env_int("TRUEMATH_GENESIS_PATTERN_THRESHOLD", 3)

# ── Swarm P2P ────────────────────────────────────────────────
SWARM_PORT: int = _env_int("TRUEMATH_SWARM_PORT", 55444)
SWARM_BROADCAST_INTERVAL: int = _env_int("TRUEMATH_SWARM_BROADCAST_INTERVAL", 5)

# ── Cognitive Context Window ─────────────────────────────────
COGNITIVE_MAX_TOKENS: int = _env_int("TRUEMATH_COGNITIVE_MAX_TOKENS", 8192)


def ensure_runtime_dirs() -> None:
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
    Path(STATE_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(GRAVEYARD_DB_PATH).parent.mkdir(parents=True, exist_ok=True)


def validate_runtime() -> None:
    errors: list[str] = []

    asset_dir = Path(DASHBOARD_ASSET_DIR)
    if not (asset_dir / "index.html").exists():
        errors.append(
            f"Dashboard build not found at '{asset_dir}'. Run scripts/build-ui.ps1 before launching."
        )

    if IPC_PORT == DASHBOARD_PORT and IPC_HOST == DASHBOARD_HOST:
        errors.append("IPC and dashboard endpoints cannot share the same host/port pair.")

    if not _is_valid_port(IPC_PORT):
        errors.append("IPC port must be between 1 and 65535.")

    if not _is_valid_port(DASHBOARD_PORT):
        errors.append("Dashboard port must be between 1 and 65535.")

    if not _is_valid_port(SWARM_PORT):
        errors.append("Swarm port must be between 1 and 65535.")

    if not _is_loopback_host(IPC_HOST):
        errors.append("IPC host must stay on a loopback interface for desktop security.")

    if not _is_loopback_host(DASHBOARD_HOST):
        errors.append("Dashboard host must stay on a loopback interface for desktop security.")

    if DESKTOP_WIDTH < 960 or DESKTOP_HEIGHT < 640:
        errors.append("Desktop window size must be at least 960x640.")

    if AUTO_EXIT_AFTER_SECONDS < 0:
        errors.append("Auto-exit duration cannot be negative.")

    if errors:
        raise RuntimeError("\n".join(errors))
