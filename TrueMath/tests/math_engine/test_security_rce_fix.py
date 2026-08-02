"""
SECURITY REGRESSION TESTS.

These tests exist because a real Remote Code Execution (RCE) vulnerability
was found during a security review: sympy's eval-based expression parser
(parse_expr) allowed a submitted "math question" like
`__import__("os").system("...")` to execute arbitrary shell commands on
the server. This file locks in the fix (safe_expr_parser.py's AST
whitelist + locked-down global_dict) so it can never silently regress.

If any test in this file starts failing, DO NOT weaken the validator to
make it pass — that would reopen a code-execution hole. Investigate why
the fix stopped working instead.
"""
import pytest

from src.math_engine.safe_expr_parser import UnsafeExpressionError, validate_safe_expression


class TestSafeExprParserBlocksRealAttacks:
    """Each of these is a real, working exploit that was confirmed to
    execute code before the fix — not a theoretical/hypothetical pattern."""

    def test_blocks_direct_builtins_import(self):
        with pytest.raises(UnsafeExpressionError):
            validate_safe_expression('__import__("os").system("whoami")')

    def test_blocks_class_hierarchy_walk_sandbox_escape(self):
        # The classic Python eval() sandbox escape: walk from any object to
        # `object`, then to its loaded subclasses, to find something
        # dangerous (e.g. subprocess.Popen) already in memory.
        with pytest.raises(UnsafeExpressionError):
            validate_safe_expression("().__class__.__base__.__subclasses__()")

    def test_blocks_class_hierarchy_walk_via_list_literal(self):
        with pytest.raises(UnsafeExpressionError):
            validate_safe_expression("[].__class__.__mro__[1].__subclasses__()")

    def test_blocks_file_read_via_open(self):
        with pytest.raises(UnsafeExpressionError):
            validate_safe_expression('open("/etc/passwd").read()')

    def test_blocks_lambda_wrapped_injection(self):
        with pytest.raises(UnsafeExpressionError):
            validate_safe_expression('(lambda: __import__("os").system("ls"))()')

    def test_blocks_any_dunder_attribute_access(self):
        with pytest.raises(UnsafeExpressionError):
            validate_safe_expression("x.__class__")

    def test_blocks_string_literals(self):
        # String literals are the building block of most injection payloads
        # (module names, shell commands, file paths) — banned outright,
        # since no legitimate math expression needs a string literal.
        with pytest.raises(UnsafeExpressionError):
            validate_safe_expression('"a" + "b"')

    def test_blocks_subscripting(self):
        with pytest.raises(UnsafeExpressionError):
            validate_safe_expression("x[0]")

    def test_blocks_attribute_calls_not_just_dunders(self):
        # Even a non-dunder attribute call should be rejected — only plain
        # function-name calls like sin(x) are legitimate math syntax.
        with pytest.raises(UnsafeExpressionError):
            validate_safe_expression("x.bit_length()")


class TestSafeExprParserAllowsRealMath:
    """Every one of these MUST keep working — the fix must not break
    legitimate math expressions."""

    @pytest.mark.parametrize("expr", [
        "x**2 + sin(x)",
        "2*x + 5 - 3",
        "sqrt(x) * cos(y)",
        "(x+1)*(x-1)",
        "-x**2",
        "exp(x) + log(x)",
        "x**2 - 4",
        "Derivative(y(x), x, x)",
        "3.14159 * x",
    ])
    def test_allows_expression(self, expr):
        validate_safe_expression(expr)  # must not raise


class TestEndToEndSecurityViaPublicAPI:
    """Confirms the fix is actually wired into the real entry points a
    remote user would hit (not just the validator in isolation)."""

    def test_problem_solver_blocks_injection_end_to_end(self):
        from src.math_engine.problem_solver import try_solve
        result = try_solve('derivative of __import__("os").system("id")')
        assert result is None  # must NOT execute, must NOT return a result

    def test_differential_equations_blocks_injection_end_to_end(self):
        from src.math_engine.differential_equations import solve_ode
        result = solve_ode('__import__("os").system("id")')
        assert result["status"] == "error"

    def test_differential_equations_blocks_injection_via_initial_conditions(self):
        from src.math_engine.differential_equations import solve_ode
        result = solve_ode("y' - y", ics={"y(0)": '__import__("os").system("id")'})
        assert result["status"] == "error"
