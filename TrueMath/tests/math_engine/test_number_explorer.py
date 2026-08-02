from src.math_engine.number_explorer import explore_number


def test_perfect_number_detects_euclid_euler_connection():
    result = explore_number(8128, include_oeis=False)
    assert result["is_perfect_number"] is True
    assert result["prime_factors"] == [2, 2, 2, 2, 2, 2, 127]
    assert any("Euclid-Euler" in f for f in result["findings"])


def test_twin_prime_detected():
    result = explore_number(17, include_oeis=False)
    assert result["is_prime"] is True
    assert result["twin_prime_partner"] == 19


def test_mersenne_prime_detected():
    result = explore_number(127, include_oeis=False)
    assert result["is_prime"] is True
    assert result["is_mersenne_prime"] is True


def test_composite_number_shows_factorization():
    result = explore_number(360, include_oeis=False)
    assert result["is_prime"] is False
    assert result["prime_factors"] == [2, 2, 2, 3, 3, 5]
    assert result["is_perfect_number"] is False


def test_invalid_input_rejected():
    result = explore_number(-5, include_oeis=False)
    assert result["status"] == "error"
