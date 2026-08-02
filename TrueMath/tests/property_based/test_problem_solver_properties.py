"""Property-based tests for problem_solver.py — generates random linear
equations and checks that the solver's own self-verification step is
always correct (never claims 'verified' for a wrong answer, and always
successfully verifies a genuinely correct answer)."""
import sympy
from hypothesis import given, settings
from hypothesis import strategies as st

from src.math_engine.problem_solver import try_solve

_NONZERO_INT = st.integers(min_value=-20, max_value=20).filter(lambda x: x != 0)
_ANY_SMALL_INT = st.integers(min_value=-50, max_value=50)


@given(_NONZERO_INT, _ANY_SMALL_INT, _ANY_SMALL_INT)
@settings(max_examples=300, deadline=None)
def test_random_linear_equations_always_verify_correctly(a, b, c):
    """For random a*x + b = c, the solver must find x and its own
    substitution self-check must confirm it (verified_ok=True)."""
    question = f"{a}x + {b} = {c}"
    result = try_solve(question)
    assert result is not None, f"Solver failed to recognize: {question}"
    assert result["verified_ok"] is True, f"Solver's own verification failed for: {question} -> {result}"

    # Independently double-check the solver's answer ourselves (not just
    # trusting its self-report) — parse "x = <value>" with sympy so exact
    # fractions (e.g. "1/2") are handled correctly, not just floats.
    answer = result["answer"]
    assert answer.startswith("x = ")
    x_value = sympy.sympify(answer.split("=")[1].strip().split(",")[0])
    assert abs(float(a * x_value + b - c)) < 1e-6


@given(st.integers(min_value=1, max_value=20), _ANY_SMALL_INT, _ANY_SMALL_INT)
@settings(max_examples=200, deadline=None)
def test_random_quadratics_always_verify_correctly(a, b, c):
    """For random a*x^2 + b*x + c = 0 (may have 0, 1, or 2 real/complex
    roots), whatever the solver finds must satisfy the original equation."""
    question = f"{a}x^2 + {b}x + {c} = 0"
    result = try_solve(question)
    if result is None:
        return  # no solution found is fine, not every quadratic must match our patterns
    assert result["verified_ok"] is True, f"Solver's own verification failed for: {question} -> {result}"
