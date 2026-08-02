"""
Property-based tests for number_theory.py.

Unlike example-based tests ("gcd(48,18)==6"), these check that a
mathematical PROPERTY holds for thousands of randomly generated inputs —
e.g. "gcd(a,b) must always divide both a and b" — which catches edge cases
(negative numbers, zero, huge numbers) that hand-picked examples miss.
"""
import math

from hypothesis import given, settings
from hypothesis import strategies as st

from src.math_engine.number_theory import (
    extended_gcd,
    gcd,
    is_prime,
    mod_inverse,
    prime_factors,
)

_SMALL_INT = st.integers(min_value=1, max_value=10_000)
_ANY_INT = st.integers(min_value=-10_000, max_value=10_000)


@given(_SMALL_INT, _SMALL_INT)
@settings(max_examples=300)
def test_gcd_divides_both_numbers(a, b):
    g = gcd(a, b)
    assert a % g == 0
    assert b % g == 0


@given(_ANY_INT, _ANY_INT)
@settings(max_examples=300)
def test_extended_gcd_satisfies_bezouts_identity(a, b):
    if a == 0 and b == 0:
        return  # gcd(0,0) is degenerate, skip
    g, x, y = extended_gcd(a, b)
    assert a * x + b * y == g
    assert g == math.gcd(a, b)


@given(st.integers(min_value=1, max_value=1000), st.integers(min_value=2, max_value=1000))
@settings(max_examples=300)
def test_mod_inverse_roundtrip_when_it_exists(a, m):
    inv = mod_inverse(a, m)
    if inv is not None:
        assert (a * inv) % m == 1
    else:
        # If no inverse was returned, gcd(a, m) must genuinely not be 1
        assert math.gcd(a, m) != 1


@given(st.integers(min_value=2, max_value=100_000))
@settings(max_examples=300)
def test_is_prime_matches_trial_division(n):
    # Cross-check our Miller-Rabin implementation against brute-force
    # trial division (slow but unambiguously correct for this range).
    def trial_division_is_prime(k):
        if k < 2:
            return False
        for i in range(2, int(k ** 0.5) + 1):
            if k % i == 0:
                return False
        return True

    assert is_prime(n) == trial_division_is_prime(n)


@given(st.integers(min_value=2, max_value=1_000_000))
@settings(max_examples=200)
def test_prime_factors_multiply_back_to_original(n):
    factors = prime_factors(n)
    product = 1
    for f in factors:
        product *= f
    assert product == n
    for f in factors:
        assert is_prime(f)
