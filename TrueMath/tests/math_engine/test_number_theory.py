import pytest

from src.math_engine.number_theory import (
    FactorizationTimeoutError,
    chinese_remainder,
    extended_gcd,
    gcd,
    is_prime,
    lcm,
    mod_inverse,
    mod_pow,
    prime_factors,
    solve_linear_diophantine,
)


def test_gcd_lcm():
    assert gcd(48, 18) == 6
    assert lcm(4, 6) == 12
    assert gcd(0, 5) == 5
    assert lcm(0, 5) == 0


def test_extended_gcd():
    g, x, y = extended_gcd(35, 15)
    assert g == 5
    assert 35 * x + 15 * y == g


def test_mod_inverse():
    assert mod_inverse(3, 11) == 4
    assert (3 * 4) % 11 == 1
    assert mod_inverse(2, 4) is None  # gcd(2,4) != 1, no inverse exists


def test_mod_pow():
    assert mod_pow(2, 10, 1000) == 24
    assert mod_pow(7, 0, 13) == 1


@pytest.mark.parametrize("n,expected", [
    (97, True), (100, False), (2, True), (1, False), (0, False),
    (982451653, True),  # known large prime
])
def test_is_prime(n, expected):
    assert is_prime(n) == expected


def test_prime_factors():
    assert prime_factors(360) == [2, 2, 2, 3, 3, 5]
    assert prime_factors(1) == []
    assert prime_factors(97) == [97]
    # Large semiprime — exercises Pollard's rho, not just trial division
    p, q = 1000000007, 999999937
    assert prime_factors(p * q) == sorted([p, q])


def test_chinese_remainder():
    x = chinese_remainder([2, 3, 2], [3, 5, 7])
    assert x % 3 == 2
    assert x % 5 == 3
    assert x % 7 == 2


def test_linear_diophantine():
    result = solve_linear_diophantine(6, 10, 4)
    assert result is not None
    x0, y0, _general = result
    assert 6 * x0 + 10 * y0 == 4

    # No solution: gcd(4, 6) = 2 does not divide 5
    assert solve_linear_diophantine(4, 6, 5) is None


def test_prime_factors_times_out_gracefully_on_hard_semiprime():
    """SECURITY: factoring a deliberately hard-to-factor large semiprime
    must fail with a clear exception within the time budget, not hang the
    calling thread indefinitely (confirmed as a real DoS vector — an
    unbounded attempt didn't complete within 8+ seconds)."""
    import time
    hard_semiprime = 999999999999999999999999999989 * 999999999999999999999999999999999
    t0 = time.time()
    with pytest.raises(FactorizationTimeoutError):
        prime_factors(hard_semiprime, timeout_seconds=2.0)
    elapsed = time.time() - t0
    assert elapsed < 4.0  # should stop close to the requested timeout, not hang
