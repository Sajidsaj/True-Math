from src.math_engine.problem_solver import try_solve


def test_linear_equation():
    result = try_solve("2x + 5 = 15")
    assert result is not None
    assert result["answer"] == "x = 5"
    assert result["verified_ok"] is True


def test_quadratic_equation():
    result = try_solve("x^2 - 9 = 0")
    assert result is not None
    assert "-3" in result["answer"] and "3" in result["answer"]
    assert result["verified_ok"] is True
    assert result["graph"] is not None


def test_derivative():
    result = try_solve("derivative of x^3")
    assert result is not None
    assert "3*x**2" in result["answer"]
    assert result["verified_ok"] is True


def test_integral():
    result = try_solve("integrate x^2")
    assert result is not None
    assert "x**3/3" in result["answer"]


def test_simplify():
    result = try_solve("simplify (x^2-1)/(x-1)")
    assert result is not None
    assert "x + 1" in result["answer"]


def test_simplify_reports_genuine_operation_count_reduction():
    result = try_solve("simplify (x**3 + 3*x**2 + 3*x + 1)/(x + 1)")
    assert result is not None
    assert "(x + 1)**2" in result["answer"]
    assert "shorter" in result["answer"]
    # The pipeline must show at least the original + one reduction step
    assert len(result["steps"]) >= 2
    assert "Original" in result["steps"][0]


def test_factor():
    result = try_solve("factor x^2 - 9")
    assert result is not None
    assert "x - 3" in result["answer"] and "x + 3" in result["answer"]


def test_arithmetic():
    result = try_solve("2 + 2 * 5")
    assert result is not None
    assert "12" in result["answer"]


def test_plot():
    result = try_solve("plot x^2 - 4")
    assert result is not None
    assert result["graph"] is not None
    assert len(result["graph"]["points"]) > 5


def test_non_computable_returns_none():
    # Open-ended conceptual questions aren't handled by the symbolic
    # solver — the caller should fall back to the LLM tutor for these.
    assert try_solve("what is calculus") is None
    assert try_solve("explain the pythagorean theorem") is None


def test_answer_includes_latex():
    result = try_solve("2x + 5 = 15")
    assert result.get("answer_latex")
    assert "x" in result["answer_latex"]
