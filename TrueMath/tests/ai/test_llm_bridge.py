import pytest
import json
from unittest.mock import patch, MagicMock
from src.ai.llm_bridge import LocalLLMBridge

def test_llm_successful_response():
    bridge = LocalLLMBridge(timeout=2)
    mock_payload = b'{"response": "x + 2 = 5 requires x = 3"}'
    
    # Mock Native urllib completely protecting the Unit Tests from requiring OS AI binaries
    with patch("urllib.request.urlopen") as mock_url:
        cm = MagicMock()
        cm.status = 200
        cm.read.return_value = mock_payload
        mock_url.return_value.__enter__.return_value = cm
        
        result = bridge.prompt_ai("SYSTEM", "MATH")
        assert result == "x + 2 = 5 requires x = 3"

def test_llm_json_corruption_handling():
    """Verify system blocks randomly destroyed packet buffers natively."""
    bridge = LocalLLMBridge(timeout=2)
    mock_payload = b'{"response": "x + ' # Specifically truncated fatal JSON
    
    with patch("urllib.request.urlopen") as mock_url:
        cm = MagicMock()
        cm.status = 200
        cm.read.return_value = mock_payload
        mock_url.return_value.__enter__.return_value = cm
        
        result = bridge.prompt_ai("SYTEM", "MATH")
        assert result is None # Fails gracefully!
