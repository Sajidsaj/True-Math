import pytest
from unittest.mock import patch, MagicMock
import subprocess
from src.math_engine.lean4_bridge import Lean4Bridge, FormalVerificationKernelError

# Since tests shouldn't require Lean physically installed to pass structural module CI,
# we patch shutil.which to simulate Lean 4 being available, and mock subprocess.run.


def test_lean4_success_pipeline():
    with patch("shutil.which", return_value="/usr/bin/lean"):
        bridge = Lean4Bridge(timeout_seconds=5)

    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "theorem main : 1 + 1 = 2 := rfl"
        mock_run.return_value = mock_result

        status, log = bridge.verify_theorem("theorem main : 1 + 1 = 2 := rfl")
        assert status is True
        assert log == mock_result.stdout


def test_lean4_failure_pipeline():
    with patch("shutil.which", return_value="/usr/bin/lean"):
        bridge = Lean4Bridge(timeout_seconds=5)

    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "error: unable to synthesize type class instance"
        mock_run.return_value = mock_result

        status, log = bridge.verify_theorem("theorem main : 1 + 1 = 3 := rfl")
        assert status is False
        assert log == mock_result.stderr


def test_lean4_timeout_protection():
    with patch("shutil.which", return_value="/usr/bin/lean"):
        bridge = Lean4Bridge(timeout_seconds=2)

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["lean", "temp"], timeout=2)):
        status, log = bridge.verify_theorem("theorem complex_proof ...")
        assert status is False
        assert "TIMEOUT" in log
