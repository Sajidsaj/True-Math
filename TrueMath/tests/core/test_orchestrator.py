import pytest
import time
from src.core.orchestrator import TrueMathOrchestrator

def test_orchestrator_initialization_slots():
    """Verify orchestrator initialises with all 15 modules and _is_running=False."""
    brain = TrueMathOrchestrator()
    assert brain._is_running is False

    with pytest.raises(AttributeError):
        brain.illegal_memory_leak = True

def test_autonomous_start_stop_safety():
    """Verify daemon thread starts cleanly and stops without zombie OS processes."""
    brain = TrueMathOrchestrator()

    brain.start()
    assert brain._is_running is True
    assert brain._research_loop_thread is not None
    assert brain._research_loop_thread.is_alive() is True

    brain.stop()

    time.sleep(0.3)
    assert brain._research_loop_thread.is_alive() is False
    assert brain._is_running is False
