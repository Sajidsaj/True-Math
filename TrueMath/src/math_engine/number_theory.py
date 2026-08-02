"""
Module Name: number_theory
Purpose: Real, standard number-theory algorithms — usable both as a plain
         Python library (import and call directly) and via the TrueMath
         dashboard/IPC layer.
Responsibilities:
  - GCD/LCM, extended Euclidean algorithm, modular inverse, modular
    exponentiation.
  - Primality testing (deterministic Miller-Rabin for 64-bit range).
  - Prime factorization (trial division + Pollard's rho for large factors).
  - Chinese Remainder Theorem.
  - Linear Diophantine equation solving (ax + by = c).
Dependencies: none (pure Python, uses random for Pollard's rho)
Honesty note: These are textbook algorithms, not novel research — but they
              are genuinely correct, general-purpose implementations you
              can rely on in real code (e.g. RSA-style modular arithmetic,
              CRT-based scheduling, basic factoring).
"""
from __future__ import annotations

import math
import random
import time
from typing import List, Optional, Tuple


def gcd(a: int, b: int) -> int:
    return math.gcd(a, b)


def lcm(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return abs(a * b) // math.gcd(a, b)


def extended_gcd(a: int, b: int) -> Tuple[int, int, int]:
    """Returns (g, x, y) such that a*x + b*y = g = gcd(a, b).
    g is always non-negative, matching the standard convention (and
    math.gcd's behavior) — even when a and/or b are negative."""
    old_r, r = a, b
    old_s, s = 1, 0
    old_t, t = 0, 1
    while r != 0:
        q = old_r // r
        old_r, r = r, old_r - q * r
        old_s, s = s, old_s - q * s
        old_t, t = t, old_t - q * t
    if old_r < 0:
        # Normalize sign so g matches gcd()'s non-negative convention,
        # adjusting x, y to keep a*x + b*y = g true.
        old_r, old_s, old_t = -old_r, -old_s, -old_t
    return old_r, old_s, old_t


def mod_inverse(a: int, m: int) -> Optional[int]:
    """Modular multiplicative inverse of a mod m, or None if it doesn't exist
    (i.e. gcd(a, m) != 1)."""
    g, x, _ = extended_gcd(a % m, m)
    if g != 1:
        return None
    return x % m


def mod_pow(base: int, exponent: int, modulus: int) -> int:
    """Fast modular exponentiation (base^exponent mod modulus)."""
    return pow(base, exponent, modulus)


def is_prime(n: int) -> bool:
    """Deterministic Miller-Rabin primality test — exact (not probabilistic)
    for all n within the 64-bit range using these fixed witnesses."""
    if n < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if n % p == 0:
            return n == p

    d, r = n - 1, 0
    while d % 2 == 0:
        d //= 2
        r += 1

    for a in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if a >= n:
            continue
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


class FactorizationTimeoutError(Exception):
    """Raised when Pollard's rho can't find a factor within the time
    budget — this is expected for very large, deliberately-hard-to-factor
    semiprimes (that difficulty is the entire basis of RSA security), not
    a bug. Without this cutoff, such a request would hang the handling
    thread indefinitely — a real DoS vector confirmed during a security
    review (an unbounded factorization attempt didn't return within 8+
    seconds and had to be killed externally)."""


def _pollard_rho(n: int, deadline: float) -> int:
    """Finds one non-trivial factor of composite n using Pollard's rho.
    `deadline` is an absolute time.monotonic() value — raises
    FactorizationTimeoutError if exceeded, rather than looping forever."""
    if n % 2 == 0:
        return 2
    x = random.randint(2, n - 1)
    y = x
    c = random.randint(1, n - 1)
    d = 1
    while d == 1:
        if time.monotonic() > deadline:
            raise FactorizationTimeoutError(
                "Factorization is taking too long — this number may have very large prime "
                "factors that are intrinsically hard to find (this is expected behavior for "
                "hard semiprimes, not an error in the algorithm)."
            )
        x = (x * x + c) % n
        y = (y * y + c) % n
        y = (y * y + c) % n
        d = math.gcd(abs(x - y), n)
    return d if d != n else _pollard_rho(n, deadline)


def prime_factors(n: int, timeout_seconds: float = 5.0) -> List[int]:
    """Full prime factorization of n (with multiplicity), sorted ascending.
    Uses trial division for small factors, then Pollard's rho for large ones
    — fast enough for numbers up to ~10^18 in reasonable time for most
    inputs (factoring is intrinsically hard for large semiprimes, same as
    for every factoring algorithm — that's the whole basis of RSA).

    Raises FactorizationTimeoutError if a hard-to-factor number exceeds
    `timeout_seconds` — see that class's docstring for why this exists."""
    if n < 2:
        return []
    factors = []
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47):
        while n % p == 0:
            factors.append(p)
            n //= p
    if n == 1:
        return factors

    deadline = time.monotonic() + timeout_seconds
    stack = [n]
    while stack:
        m = stack.pop()
        if m == 1:
            continue
        if is_prime(m):
            factors.append(m)
            continue
        d = _pollard_rho(m, deadline)
        stack.append(d)
        stack.append(m // d)
    return sorted(factors)


def chinese_remainder(remainders: List[int], moduli: List[int]) -> Optional[int]:
    """Solves x ≡ remainders[i] (mod moduli[i]) for all i simultaneously.
    Returns the smallest non-negative solution mod the product of moduli,
    or None if no solution exists (moduli must be pairwise coprime for the
    classic CRT; this implementation also handles some non-coprime cases
    via a generalized merge)."""
    x, m = 0, 1
    for r_i, m_i in zip(remainders, moduli):
        g, p, q = extended_gcd(m, m_i)
        if (r_i - x) % g != 0:
            return None  # no solution — the congruences are inconsistent
        lcm_val = m // g * m_i
        x = (x + m * ((r_i - x) // g * p % (m_i // g))) % lcm_val
        m = lcm_val
    return x % m


def solve_linear_diophantine(a: int, b: int, c: int) -> Optional[Tuple[int, int, str]]:
    """Solves ax + by = c for integers x, y. Returns (x0, y0, general_form)
    for one particular solution plus the general family, or None if no
    integer solution exists (i.e. gcd(a,b) doesn't divide c)."""
    g, x0, y0 = extended_gcd(a, b)
    if c % g != 0:
        return None
    scale = c // g
    x0, y0 = x0 * scale, y0 * scale
    general = f"x = {x0} + {b // g}*t, y = {y0} - {a // g}*t  (t = any integer)"
    return x0, y0, general
