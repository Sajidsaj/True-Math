from src.math_engine.hard_problem_dispatcher import CATEGORIES, solve


def test_solve_valid_operation():
    result = solve("number_theory", "gcd", {"a": 48, "b": 18})
    assert result["status"] == "ok"
    assert result["result"] == 6


def test_solve_missing_parameter_is_graceful():
    result = solve("number_theory", "gcd", {"a": 48})
    assert result["status"] == "error"
    assert "b" in result["message"]


def test_solve_unknown_category_is_graceful():
    result = solve("not_a_category", "op", {})
    assert result["status"] == "error"


def test_solve_unknown_operation_is_graceful():
    result = solve("number_theory", "not_an_op", {})
    assert result["status"] == "error"


def test_all_categories_have_at_least_one_operation():
    for category, operations in CATEGORIES.items():
        assert len(operations) > 0, f"{category} has no operations listed"


def test_every_listed_operation_is_actually_dispatchable():
    # Cross-check CATEGORIES against the internal dispatch table so the
    # catalog the UI shows never lists an operation that doesn't exist.
    from src.math_engine import hard_problem_dispatcher as hpd
    for category, operations in CATEGORIES.items():
        for op in operations:
            assert (category, op) in hpd._OPERATIONS, f"{category}.{op} listed but not implemented"
