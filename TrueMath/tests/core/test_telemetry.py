import pytest
from src.core.telemetry_engine import TelemetryEngine

def test_telemetry_initialization_zero_state():
    """Verify zero states math avoids domain exception parsing structures natively."""
    telemetry = TelemetryEngine()
    
    snapshot = telemetry.generate_snapshot()
    assert snapshot["lean4_success_ratio"] == 0.0
    assert snapshot["mcts_nodes"] == 0

def test_telemetry_ratio_logic():
    """Verify structurally sound native Float Math mappings."""
    telemetry = TelemetryEngine()
    
    telemetry.log_lean4_execution(success=True)
    telemetry.log_lean4_execution(success=False)
    telemetry.log_lean4_execution(success=False)
    
    # 1 success out of 3 total executions = 33.33 % natively
    snapshot = telemetry.generate_snapshot()
    assert snapshot["lean4_success_ratio"] == 33.33
    assert snapshot["lean4_executed"] == 3
