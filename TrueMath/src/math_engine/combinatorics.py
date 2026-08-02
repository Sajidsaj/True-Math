"""
Module Name: combinatorics
Purpose: Real combinatorics / competitive-programming-style algorithms —
         permutations, combinations, fast Fibonacci (matrix/doubling
         method), Catalan numbers. Exact arbitrary-precision results
         (Python big ints), not floating-point approximations.
Dependencies: math
"""
from __future__ import annotations

import math
from typing import Dict


def n_choose_r(n: int, r: int) -> int:
    """Exact binomial coefficient C(n, r)."""
    if r < 0 or r > n:
        return 0
    return math.comb(n, r)


def n_permute_r(n: int, r: int) -> int:
    """Exact number of permutations of r items chosen from n: P(n, r)."""
    if r < 0 or r > n:
        return 0
    return math.perm(n, r)


def fibonacci(n: int) -> int:
    """Fast-doubling Fibonacci: computes F(n) exactly in O(log n) big-int
    multiplications — feasible for n in the millions, unlike the naive
    O(n) or exponential recursive versions."""
    if n < 0:
        raise ValueError("n must be non-negative")

    def _fib_pair(k: int):
        if k == 0:
            return (0, 1)
        a, b = _fib_pair(k >> 1)
        c = a * (2 * b - a)
        d = a * a + b * b
        if k & 1:
            return (d, c + d)
        return (c, d)

    return _fib_pair(n)[0]


def catalan_number(n: int) -> int:
    """Exact n-th Catalan number: C_n = (2n)! / ((n+1)! n!) — counts
    balanced parenthesizations, binary trees, polygon triangulations, etc."""
    if n < 0:
        return 0
    return math.comb(2 * n, n) // (n + 1)


def combinatorics_summary(n: int, r: int) -> Dict[str, int]:
    """Convenience bundle of the common combinatorics quantities for a
    given (n, r), handy for quick coding lookups."""
    return {
        "n_choose_r": n_choose_r(n, r),
        "n_permute_r": n_permute_r(n, r),
        "fibonacci_n": fibonacci(n),
        "catalan_n": catalan_number(n),
    }
