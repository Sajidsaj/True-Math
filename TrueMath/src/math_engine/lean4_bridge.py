"""
Module Name: lean4_bridge
Purpose: A hard-isolation interface executing Lean 4 formal type-checking
         natively, using syntactically-correct Lean 4 source (via
         lean4_translator) instead of raw Python expression strings.
Responsibilities:
  - Auto-detect the Lean 4 / Lake binaries (PATH first, then elan's default
    install locations, since a freshly-installed elan often isn't on PATH
    for a process that was already running).
  - If a Mathlib-backed Lake project is configured (config.LEAN4_PROJECT_DIR)
    and built, use `lake env lean` so `import Mathlib` resolves — needed for
    anything with trig/exp/log/pi. Otherwise fall back to bare `lean` for
    pure-integer expressions, which needs no extra setup at all.
  - Spawn the Lean interpreter via `subprocess`, with a hard timeout.
Dependencies: subprocess, os, tempfile, shutil
Honesty note: A passing result here means "this is syntactically valid,
              well-typed mathematics" (a type-check), not "this is a proven
              true theorem" — the hypotheses being checked are bare
              expressions, not propositions with a proof tactic attached.
              See lean4_translator.py for details.
"""
import functools
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple

from src.core.sys_logger import get_logger

logger = get_logger("Lean4Bridge")


class FormalVerificationKernelError(Exception):
    pass


def _find_binary(name: str) -> Optional[str]:
    """Looks on PATH first, then common elan install locations, since a
    binary installed by elan moments ago often isn't on PATH yet for an
    already-running process (very common right after a fresh install)."""
    found = shutil.which(name)
    if found:
        return found

    exe = f"{name}.exe" if os.name == "nt" else name
    candidates = [
        Path.home() / ".elan" / "bin" / exe,
        Path(os.environ.get("USERPROFILE", "")) / ".elan" / "bin" / exe,
        Path("/usr/local/bin") / exe,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


class Lean4Bridge:
    __slots__ = ('workspace_dir', 'timeout_seconds', '_lean_path', '_lake_path', 'project_dir', '_mathlib_ready')

    def __init__(self, timeout_seconds: int = 30, project_dir: Optional[str] = None):
        self.workspace_dir = tempfile.gettempdir()
        self.timeout_seconds = timeout_seconds
        self.project_dir = project_dir

        self._lean_path = _find_binary("lean")
        self._lake_path = _find_binary("lake")

        if not self._lean_path:
            logger.warning(
                "Lean 4 binary not found (checked PATH and ~/.elan/bin). "
                "Formal verification will be skipped. Install from "
                "https://leanprover-community.github.io/get_started.html"
            )

        # Mathlib is only usable if there's a built Lake project configured.
        self._mathlib_ready = bool(
            self._lake_path and self.project_dir and (Path(self.project_dir) / "lakefile.lean").is_file()
        )
        if self._lean_path and not self._mathlib_ready:
            logger.info(
                "Lean 4 found, but no built Mathlib project is configured — "
                "pure-integer expressions can still be checked. Run "
                "scripts/setup-lean4.ps1 once to enable trig/exp/log checks."
            )

        logger.info(f"Lean 4 Verification Bridge initialized (lean={bool(self._lean_path)}, mathlib={self._mathlib_ready}).")

    @property
    def available(self) -> bool:
        return bool(self._lean_path)

    def verify_theorem(self, lean_source: str, needs_mathlib: bool = False) -> Tuple[bool, str]:
        """Public API: LRU-cached Lean 4 type-check.

        BUG-08 FIX (kept): cache is a module-level function so it doesn't
        hold a strong reference to `self`, avoiding a permanent memory leak.
        """
        if not self._lean_path:
            return False, "SKIPPED: Lean 4 binary not available."
        if needs_mathlib and not self._mathlib_ready:
            return False, (
                "SKIPPED: this expression needs Mathlib (trig/exp/log/pi), but no built "
                "Mathlib project is configured. Run scripts/setup-lean4.ps1 once."
            )

        lake_env = self._lake_path if (needs_mathlib and self._mathlib_ready) else None
        return _cached_verify(
            lean_source, self.workspace_dir, self.timeout_seconds,
            self._lean_path, lake_env, self.project_dir if needs_mathlib else None,
        )


@functools.lru_cache(maxsize=16384)
def _cached_verify(
    lean_source: str,
    workspace_dir: str,
    timeout_seconds: int,
    lean_path: str,
    lake_path: Optional[str],
    project_dir: Optional[str],
) -> Tuple[bool, str]:
    """Module-level cached Lean 4 subprocess runner (not an instance method,
    so lru_cache never captures `self` — see BUG-08 in the changelog)."""
    fd, temp_path = tempfile.mkstemp(suffix=".lean", dir=workspace_dir)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(lean_source)
    except OSError as e:
        logger.error(f"Cannot write Lean4 temp file: {e}")
        raise FormalVerificationKernelError("OS file isolation failure.")

    try:
        if lake_path and project_dir:
            # `lake env lean` runs lean with the project's Mathlib on its
            # search path, so `import Mathlib` resolves.
            cmd = [lake_path, "env", "lean", temp_path]
            cwd = project_dir
        else:
            cmd = [lean_path, temp_path]
            cwd = None

        logger.debug(f"Dispatching to Lean 4: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_seconds, cwd=cwd)

        if result.returncode == 0:
            logger.info("Lean 4 PASS: expression type-checks as valid mathematics.")
            return True, result.stdout.strip()
        else:
            logger.warning("Lean 4 FAIL: expression rejected by the type checker.")
            return False, result.stderr.strip()
    except subprocess.TimeoutExpired:
        logger.error(f"Lean 4 timed out after {timeout_seconds}s.")
        return False, "TIMEOUT: type-check exceeded CPU time budget."
    except FileNotFoundError:
        logger.critical("Lean 4 / Lake binary vanished between detection and execution.")
        raise FormalVerificationKernelError("Lean 4 executable not found in system PATH.")
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass
