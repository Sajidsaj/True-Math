import pytest

from src.math_engine.statistics_tool import describe, linear_regression


def test_describe():
    result = describe([2, 4, 4, 4, 5, 5, 7, 9])
    assert result["status"] == "ok"
    assert result["mean"] == 5
    assert result["median"] == 4.5
    assert result["mode"] == 4
    assert result["min"] == 2
    assert result["max"] == 9
    assert result["stdev"] == pytest.approx(2.138, abs=0.001)


def test_describe_empty():
    result = describe([])
    assert result["status"] == "error"


def test_linear_regression_perfect_line():
    result = linear_regression([1, 2, 3, 4, 5], [2, 4, 6, 8, 10])
    assert result["slope"] == pytest.approx(2.0)
    assert result["intercept"] == pytest.approx(0.0, abs=1e-9)
    assert result["correlation_r"] == pytest.approx(1.0)


def test_linear_regression_vertical_line_undefined():
    result = linear_regression([5, 5, 5], [1, 2, 3])
    assert result["status"] == "error"
