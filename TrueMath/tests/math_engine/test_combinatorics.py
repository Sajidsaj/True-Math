from src.math_engine.combinatorics import catalan_number, fibonacci, n_choose_r, n_permute_r


def test_n_choose_r():
    assert n_choose_r(10, 3) == 120
    assert n_choose_r(5, 0) == 1
    assert n_choose_r(5, 6) == 0  # r > n


def test_n_permute_r():
    assert n_permute_r(10, 3) == 720


def test_fibonacci():
    assert fibonacci(0) == 0
    assert fibonacci(1) == 1
    assert fibonacci(50) == 12586269025
    # Fast-doubling must agree with the naive recurrence for a bigger n
    assert len(str(fibonacci(1000))) == 209


def test_catalan_number():
    assert catalan_number(0) == 1
    assert catalan_number(5) == 42
