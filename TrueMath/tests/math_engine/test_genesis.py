import pytest
from src.math_engine.symbolic_genesis import SymbolicGenesisCore, ExtractedOperator

def test_no_pattern_extraction_on_chaos():
    """Verify Genesis engine ignores completely random chaotic mathematical branches."""
    genesis = SymbolicGenesisCore(pattern_threshold=3)
    trace = ["add", "sub", "mul", "div", "sin", "cos", "tan", "log"]
    
    op = genesis.scan_for_abstractions(trace)
    assert op is None # No repetition exists

def test_pattern_abstraction_identification():
    """Verify that highly repetitive loop structures trigger a new Operator synthesis."""
    genesis = SymbolicGenesisCore(pattern_threshold=3)
    
    # 12 elements: ('derive','integrate','simplify') repeats 4 times — beats any 2-gram
    trace = ["derive", "integrate", "simplify"] * 4
    
    op = genesis.scan_for_abstractions(trace)
    assert op is not None
    assert op.symbol_id == "OP_GEN_1"
    assert op.occurrences >= 3
    assert "derive" in op.pattern_signature

def test_threshold_enforcement():
    """Verify limits are respected to prevent junk-symbol inflation."""
    genesis = SymbolicGenesisCore(pattern_threshold=4)
    # Pattern ('add',) repeats 3 times — below the threshold of 4, so nothing is invented
    trace = ["add", "sub", "add", "sub", "add", "sub"]
    
    assert genesis.scan_for_abstractions(trace) is None
