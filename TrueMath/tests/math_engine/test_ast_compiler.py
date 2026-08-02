import pytest
import sympy
from src.math_engine.ast_compiler import ASTPreFilter, MathSyntaxError, MaliciousPayloadError

def test_valid_math_parsing():
    """Verify standard algebra is successfully parsed into isolated Symbols."""
    compiler = ASTPreFilter()
    expr = compiler.parse_safe_math("x**2 + 2*sin(y)")
    
    assert isinstance(expr, sympy.Expr)
    assert expr.free_symbols == {sympy.Symbol('x'), sympy.Symbol('y')}

def test_malicious_code_injection_blocked():
    """Verify that Python OS-level prompt injections are forcefully rejected."""
    compiler = ASTPreFilter()
    
    # Attempting to load OS system module via built-in eval bypass
    with pytest.raises(MaliciousPayloadError):
        compiler.parse_safe_math("__import__('os').system('echo hacked')")

    # Attempting to access object attributes mapping to __class__
    with pytest.raises(MaliciousPayloadError):
        compiler.parse_safe_math("().__class__.__base__.__subclasses__()")

def test_invalid_math_handling():
    """Verify that pure gibberish is caught as a standard logic error."""
    compiler = ASTPreFilter()
    with pytest.raises((MathSyntaxError, TypeError, ValueError)):
        # Some invalid setups might trigger ValueError in Sympify depending on version
        compiler.parse_safe_math("x + * 2")

def test_safe_function_whitelist():
    """Ensure math functions like sqrt and log work perfectly."""
    compiler = ASTPreFilter()
    expr = compiler.parse_safe_math("sqrt(x) + log(y)")
    assert "sqrt(x) + log(y)" in str(expr)
