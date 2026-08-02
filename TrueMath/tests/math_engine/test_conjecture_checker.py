from src.math_engine.conjecture_checker import (
    check_collatz,
    check_goldbach,
    check_twin_primes,
    run_check,
    search_mersenne_primes,
    search_perfect_numbers,
)


def test_collatz_no_counterexample_in_small_range():
    result = check_collatz(1000)
    assert result["counterexample_found"] is False
    # Known: the longest chain under 1000 starts at 871 and takes 178 steps
    assert result["details"]["longest_chain_start"] == 871
    assert result["details"]["longest_chain_len"] == 178


def test_goldbach_no_counterexample_in_small_range():
    result = check_goldbach(1000)
    assert result["counterexample_found"] is False


def test_twin_primes_known_count():
    # Known value: there are 35 twin prime pairs below 1000
    result = check_twin_primes(1000)
    assert result["details"]["pairs_found"] == 35


def test_run_check_dispatches_correctly():
    result = run_check("collatz", 100)
    assert result["conjecture"] == "Collatz Conjecture"

    result_unknown = run_check("not_a_real_conjecture", 100)
    assert "Unknown" in result_unknown["summary"]


def test_perfect_numbers_matches_known_values():
    # Known: the first four perfect numbers are 6, 28, 496, 8128
    result = search_perfect_numbers(10000)
    assert result["details"]["perfect_numbers_found"] == [6, 28, 496, 8128]


def test_mersenne_primes_matches_known_exponents():
    # Known: Mersenne prime exponents up to 20 are 2, 3, 5, 7, 13, 17, 19
    result = search_mersenne_primes(20)
    exponents = [f["exponent"] for f in result["details"]["mersenne_primes_found"]]
    assert exponents == [2, 3, 5, 7, 13, 17, 19]
