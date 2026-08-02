import os
import pytest
from src.core.state_manager import EpochStateManager

def test_epoch_save_and_load(tmp_path):
    """Verify that complex JSON states are losslessly saved and restored."""
    db_path = tmp_path / "test_state.db"
    manager = EpochStateManager(str(db_path))
    
    mock_state = {
        "problem_id": "riemann_zetas_01",
        "current_depth": 42,
        "nodes_expanded": 1024,
        "active_graph": {
            "branch_A_status": "pending",
            "heuristics": [0.1, 0.5, 0.99]
        }
    }
    
    # Save operation test
    success = manager.save_epoch("epoch_001_A", mock_state)
    assert success is True
    
    # Load operation test
    recovered = manager.load_latest_epoch()
    assert recovered is not None
    assert recovered["problem_id"] == "riemann_zetas_01"
    assert recovered["current_depth"] == 42
    assert len(recovered["active_graph"]["heuristics"]) == 3

def test_loading_empty_database():
    """Verify system handles fresh starts without error."""
    manager = EpochStateManager(":memory:") # Using in-memory sqlite
    recovered = manager.load_latest_epoch()
    assert recovered is None
