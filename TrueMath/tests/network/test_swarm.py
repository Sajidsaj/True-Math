import pytest
import time
from src.network.swarm_p2p import TrueMathSwarmNode

def test_swarm_initialization():
    """Verify slots initialization memory maps cleanly."""
    node = TrueMathSwarmNode(port=50000)
    assert node.port == 50000
    assert len(node.active_peers) == 0

def test_swarm_job_processing():
    """Verify the structural handling of remote CPU payloads natively."""
    node = TrueMathSwarmNode()
    
    # Valid mathematical payload block
    response = node.process_incoming_job({"math_hash": "riemann_branch_09"})
    assert response["status"] == "processing"
    
    # Invalid structural logic
    bad_resp = node.process_incoming_job({"junk": "data"})
    assert bad_resp["status"] == "error"

def test_thread_lifecycle():
    """Ensure threading loops safely exit preventing background ghost locks."""
    node = TrueMathSwarmNode(broadcast_interval=1)
    
    node.start_discovery()
    assert node._discovery_thread is not None
    assert node._discovery_thread.is_alive() is True
    
    node.stop_discovery()
    # Waiting gracefully
    time.sleep(0.5) 
    assert node._discovery_thread.is_alive() is False
