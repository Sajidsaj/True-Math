"""
Module Name: conjecture_checker
Purpose: Actually COMPUTE numeric verification of a few famous conjectures
         over a user-chosen range — real brute-force number-crunching, not
         LLM guessing. This is genuinely useful, small-scale "research
         computing": it either finds a counterexample (which would be a
         real, notable discovery) or reports that none was found in the
         tested range (which is the honest, expected outcome for these
         famous conjectures — they've already been checked far beyond what
         a personal PC can reach).
Responsibilities:
  - Collatz conjecture: verify n -> n/2 (even) / 3n+1 (odd) reaches 1.
  - Goldbach conjecture: verify every even n > 2 is a sum of two primes.
  - Twin prime conjecture: count twin prime pairs (p, p+2) in a range.
Dependencies: none (pure Python; a sieve is used for primality)
Honesty note: These conjectures have already been verified computationally
              by professional research groups far beyond what a personal
              PC can check (Collatz into the ~2^71 range as of recent
              published results, Goldbach beyond 4*10^18). Finding "no
              counterexample" here is expected and does NOT constitute a
              proof or a new discovery — it's a small personal sanity-check
              re-run of well-established computational results.
"""
from __future__ import annotations

from typing import TypedDict

# Hard ceiling so a user-supplied limit can't accidentally hang the app for
# minutes/hours or exhaust memory.
_MAX_LIMIT = 2_000_000


class ConjectureResult(TypedDict, total=False):
    conjecture: str
    range_checked: str
    counterexample_found: bool
    counterexample: object
    summary: str
    details: dict


def _sieve_of_eratosthenes(limit: int):
    is_prime = bytearray([1]) * (limit + 1)
    is_prime[0:2] = bytearray([0, 0])
    for i in range(2, int(limit ** 0.5) + 1):
        if is_prime[i]:
            for j in range(i * i, limit + 1, i):
                is_prime[j] = 0
    return is_prime


def check_collatz(limit: int) -> ConjectureResult:
    """Verifies the Collatz conjecture for every starting value from 1 to
    `limit`: repeatedly applying n/2 (even) or 3n+1 (odd) should always
    reach 1. Tracks the longest chain found, for interest."""
    limit = max(1, min(limit, _MAX_LIMIT))
    longest_chain_start, longest_chain_len = 1, 1
    counterexample = None

    for start in range(1, limit + 1):
        n = start
        steps = 0
        seen_cap = start * 1000 + 10_000  # generous safety valve, not a real math bound
        while n != 1:
            n = n // 2 if n % 2 == 0 else 3 * n + 1
            steps += 1
            if steps > seen_cap:
                counterexample = start
                break
        if counterexample is not None:
            break
        if steps > longest_chain_len:
            longest_chain_len, longest_chain_start = steps, start

    if counterexample is not None:
        summary = f"⚠️ Possible counterexample at n={counterexample} (chain didn't reach 1 within the safety cap)."
    else:
        summary = (
            f"No counterexample found for n=1..{limit:,}. "
            f"Longest chain: starting at {longest_chain_start:,}, took {longest_chain_len:,} steps to reach 1."
        )

    return {
        "conjecture": "Collatz Conjecture",
        "range_checked": f"n = 1 to {limit:,}",
        "counterexample_found": counterexample is not None,
        "counterexample": counterexample,
        "summary": summary,
        "details": {"longest_chain_start": longest_chain_start, "longest_chain_len": longest_chain_len},
    }


def check_goldbach(limit: int) -> ConjectureResult:
    """Verifies that every even integer from 4 to `limit` is the sum of two
    primes, using a sieve for fast primality lookups."""
    limit = max(4, min(limit, _MAX_LIMIT))
    is_prime = _sieve_of_eratosthenes(limit)
    primes = [i for i in range(2, limit + 1) if is_prime[i]]

    counterexample = None
    checked = 0
    max_min_prime_gap_example = None  # the even n whose smallest valid prime pair has the largest first prime

    for n in range(4, limit + 1, 2):
        found_pair = None
        for p in primes:
            if p > n // 2 + 1:
                break
            if p <= n and is_prime[n - p]:
                found_pair = (p, n - p)
                break
        checked += 1
        if not found_pair:
            counterexample = n
            break

    if counterexample is not None:
        summary = f"⚠️ Possible counterexample: no prime pair found summing to {counterexample}."
    else:
        summary = f"No counterexample found — every even number from 4 to {limit:,} is a sum of two primes."

    return {
        "conjecture": "Goldbach Conjecture",
        "range_checked": f"even n = 4 to {limit:,}",
        "counterexample_found": counterexample is not None,
        "counterexample": counterexample,
        "summary": summary,
        "details": {"even_numbers_checked": checked},
    }


def check_twin_primes(limit: int) -> ConjectureResult:
    """Counts twin prime pairs (p, p+2) up to `limit`. Doesn't (can't)
    verify infinitude — just reports what's found in the tested range, and
    the largest pair found (bigger pairs existing is itself weak evidence
    of the conjecture, though obviously not a proof)."""
    limit = max(5, min(limit, _MAX_LIMIT))
    is_prime = _sieve_of_eratosthenes(limit)

    pairs = []
    for p in range(2, limit - 1):
        if is_prime[p] and is_prime[p + 2]:
            pairs.append((p, p + 2))

    summary = (
        f"Found {len(pairs):,} twin prime pairs up to {limit:,}. "
        f"Largest found: {pairs[-1]} (this is NOT evidence of a bound — twin primes "
        f"are conjectured to be infinite, unproven either way)."
        if pairs else f"No twin prime pairs found up to {limit:,}."
    )

    return {
        "conjecture": "Twin Prime Conjecture",
        "range_checked": f"p = 2 to {limit:,}",
        "counterexample_found": False,  # not applicable — this conjecture is about infinitude, not a per-n check
        "counterexample": None,
        "summary": summary,
        "details": {"pairs_found": len(pairs), "largest_pair": pairs[-1] if pairs else None},
    }


def search_perfect_numbers(limit: int) -> ConjectureResult:
    """Searches for perfect numbers (n whose proper divisors sum to n
    itself, e.g. 6 = 1+2+3) up to `limit`. Related to the OPEN question of
    whether any ODD perfect number exists (unsolved since antiquity — none
    has ever been found, but it's not proven impossible either). All known
    perfect numbers are even and correspond to Mersenne primes (Euclid-Euler
    theorem)."""
    limit = max(2, min(limit, _MAX_LIMIT))
    is_prime = _sieve_of_eratosthenes(limit)
    perfects = []

    for n in range(2, limit + 1):
        divisor_sum = 1  # 1 always divides n (for n > 1)
        for d in range(2, int(n ** 0.5) + 1):
            if n % d == 0:
                divisor_sum += d
                if d != n // d:
                    divisor_sum += n // d
        if divisor_sum == n:
            perfects.append(n)

    summary = (
        f"Found {len(perfects)} perfect number(s) up to {limit:,}: {perfects}. "
        f"All are even, as expected (no odd perfect number has ever been found — "
        f"whether one exists is a genuinely OPEN problem in number theory)."
        if perfects else f"No perfect numbers found up to {limit:,} (they're rare — the first four are 6, 28, 496, 8128)."
    )

    return {
        "conjecture": "Perfect Numbers Search (Odd Perfect Number question)",
        "range_checked": f"n = 2 to {limit:,}",
        "counterexample_found": False,
        "counterexample": None,
        "summary": summary,
        "details": {"perfect_numbers_found": perfects},
    }


def search_mersenne_primes(max_exponent: int) -> ConjectureResult:
    """Searches for Mersenne primes (primes of the form 2^p - 1) for
    exponents p up to `max_exponent`. Related to the OPEN question of
    whether infinitely many Mersenne primes exist (unproven either way —
    51 are known as of recent searches, all found by massive distributed
    computing projects like GIMPS, far beyond what this can reach)."""
    max_exponent = max(2, min(max_exponent, 64))  # 2^64 is already a huge number to factor
    found = []
    for p in range(2, max_exponent + 1):
        candidate = 2 ** p - 1
        if _is_prime_trial(candidate):
            found.append({"exponent": p, "value": candidate})

    summary = (
        f"Found {len(found)} Mersenne prime(s) for exponents 2 to {max_exponent}: "
        f"{[f['exponent'] for f in found]}. Whether infinitely many exist is a genuinely "
        f"OPEN question — unproven either way, being actively searched by distributed "
        f"computing projects (GIMPS) at exponents far beyond what a personal PC can check."
    )

    return {
        "conjecture": "Mersenne Prime Search (infinitude question)",
        "range_checked": f"exponent p = 2 to {max_exponent}",
        "counterexample_found": False,
        "counterexample": None,
        "summary": summary,
        "details": {"mersenne_primes_found": found},
    }


def _is_prime_trial(n: int) -> bool:
    """Simple trial-division primality test for the (possibly huge) Mersenne
    candidates — good enough for the small exponent range this function is
    restricted to."""
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(n ** 0.5) + 1, 2):
        if n % i == 0:
            return False
    return True


_CHECKERS = {
    "collatz": check_collatz,
    "goldbach": check_goldbach,
    "twin_primes": check_twin_primes,
    "perfect_numbers": search_perfect_numbers,
    "mersenne_primes": search_mersenne_primes,
}


def run_check(conjecture_key: str, limit: int) -> ConjectureResult:
    fn = _CHECKERS.get(conjecture_key)
    if fn is None:
        return {
            "conjecture": conjecture_key,
            "range_checked": "",
            "counterexample_found": False,
            "summary": f"Unknown conjecture '{conjecture_key}'. Supported: {', '.join(_CHECKERS)}.",
            "details": {},
        }
    return fn(limit)
