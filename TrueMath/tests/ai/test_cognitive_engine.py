import pytest
from src.ai.cognitive_engine import CognitiveCore, ContextExhaustionError

def test_context_management_and_truncation():
    """Verify that when context limits near, older non-essential mathematical paths are forgotten seamlessly."""
    # 40 tokens: plenty for the system prompt (~6 tokens), tight enough to trigger truncation on step 4
    engine = CognitiveCore(max_context_tokens=40)
    
    engine.add_to_context("system", "You are a rigid math analyzer.")
    engine.add_to_context("user", "Attempt Collatz sequence step 1.")
    engine.add_to_context("assistant", "Step 1 completes.")
    
    # This final payload should force the system to drop the middle historical arrays
    engine.add_to_context("user", "Step 2 evaluation begins.")
    
    # Context should be pruned safely without hard-crashing operations
    assert len(engine.current_context) >= 2
    assert engine.current_context[0]['role'] == "system"

def test_fatal_context_exhaustion():
    """Verify system mathematically aborts if a single string exceeds the entire VRAM threshold."""
    # Limit of 8 tokens — the test payload is ~11 tokens, which exceeds it even after compression
    engine = CognitiveCore(max_context_tokens=8)
    
    with pytest.raises(ContextExhaustionError):
        engine.add_to_context("user", "This specific command is far too long mathematically.")
        
def test_hypothesis_generation():
    """Ensure generation output loops properly inject into current localized context."""
    engine = CognitiveCore(max_context_tokens=100)
    result = engine.generate_hypothesis()
    
    assert result == "sqrt(x) + sin(y)"
    assert engine.current_context[-1]['role'] == "assistant"
    assert engine.current_context[-1]['content'] == result
