import pytest
import math
from src.math_engine.falsification_engine import FalsificationEngine

def test_falsification_rejects_false_math():
    """Verify that a formally bad equation is statistically crushed instantly."""
    engine = FalsificationEngine(iterations=500)
    
    # We claim algebraically that "x * 2 == x + 2" (Which is only true for x=2, but false universally!)
    bad_theory = lambda x: (x * 2) == (x + 2)
    
    # Assert that the engine successfully disproves it by finding counter-examples
    assert engine.structural_brute_force(bad_theory, vars_expected=1) is False

def test_falsification_accepts_tautology():
    """Verify that objectively true algebraic transformations survive the noise loop."""
    engine = FalsificationEngine(iterations=500)
    
    # Fundamental true algebra: (x + y)^2 == x^2 + 2xy + y^2
    # We use math.isclose to handle native Python floating point inaccuracy
    good_theory = lambda x, y: math.isclose((x + y)**2, (x**2 + 2*x*y + y**2), rel_tol=1e-5)
    
    # This should mathematically survive all 500 stochastic noise tests!
    assert engine.structural_brute_force(good_theory, vars_expected=2) is True

def test_error_absorption():
    """Verify engine handles bad fractional derivations without kernel panic."""
    engine = FalsificationEngine(iterations=100)
    
    # Passing 0 into this lambda throws ZeroDivisionError
    unstable_theory = lambda x: (10 / x) == 5
    
    assert engine.structural_brute_force(unstable_theory, vars_expected=1) is False
