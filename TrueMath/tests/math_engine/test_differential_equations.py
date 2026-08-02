from src.math_engine.differential_equations import solve_ode


def test_first_order_linear_ode():
    result = solve_ode("y' - y")
    assert result["status"] == "ok"
    assert "exp(x)" in result["solution"]


def test_second_order_ode():
    result = solve_ode("y'' + y")
    assert result["status"] == "ok"
    assert "sin(x)" in result["solution"]
    assert "cos(x)" in result["solution"]


def test_ode_with_initial_condition():
    result = solve_ode("y' - y", ics={"y(0)": 1})
    assert result["status"] == "ok"
    # With y(0)=1, the constant resolves and the solution is exactly exp(x)
    assert "C1" not in result["solution"]
    assert "exp(x)" in result["solution"]
