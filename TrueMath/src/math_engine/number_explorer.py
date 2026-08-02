"""
Module Name: number_explorer
Purpose: A single-input "explore this number" feature that automatically
         runs several relevant checks together — primality, factorization,
         perfect-number membership, twin-prime/Mersenne relationships, and
         an OEIS database lookup — instead of the user manually running
         each tool separately and connecting the dots themselves.
Responsibilities:
  - Take one integer and run every DETERMINISTIC check that's cheap enough
    to always run (no LLM involved — this is pure computation, so it's
    reliable regardless of API keys/rate limits).
  - Detect interesting relationships between the results (e.g. "this is a
    perfect number AND its cofactor is a Mersenne prime").
  - Optionally include an OEIS lookup (real network call; degrades
    gracefully if offline).
Dependencies: number_theory, conjecture_checker, oeis_lookup (all local)
Honesty note: This automates ROUTING between existing, already-verified
              tools — it does not add any new mathematical capability
              beyond what each tool already does on its own. The "combined
              report" is assembled by ordinary Python logic (if/else
              pattern detection on the results), not by an LLM deciding
              what to run — this keeps it deterministic and reliable even
              when no AI provider is configured or reachable.
"""
from __future__ import annotations

from typing import Dict, List

from src.math_engine.number_theory import is_prime, prime_factors
from src.math_engine.oeis_lookup import lookup_sequence


def _is_perfect_number(n: int) -> bool:
    if n < 2:
        return False
    divisor_sum = 1
    i = 2
    while i * i <= n:
        if n % i == 0:
            divisor_sum += i
            if i != n // i:
                divisor_sum += n // i
        i += 1
    return divisor_sum == n


def _is_mersenne_prime(n: int) -> bool:
    """Checks if n is of the form 2^p - 1 for some prime p, and is itself prime."""
    if n < 3:
        return False
    candidate = n + 1
    # candidate must be a power of 2
    if candidate & (candidate - 1) != 0:
        return False
    return is_prime(n)


def explore_number(n: int, include_oeis: bool = True) -> Dict:
    """Runs every relevant deterministic check on `n` and assembles a
    combined report — the single-input version of manually running
    Conjecture Checker + Hard Problem Solver + OEIS lookup separately."""
    if not isinstance(n, int) or n < 1:
        return {"status": "error", "message": "Ek positive integer do."}

    findings: List[str] = []

    prime = is_prime(n)
    factors = prime_factors(n)
    perfect = _is_perfect_number(n)
    mersenne = _is_mersenne_prime(n)
    twin_prime_partner = None
    if prime:
        if is_prime(n + 2):
            twin_prime_partner = n + 2
        elif n > 2 and is_prime(n - 2):
            twin_prime_partner = n - 2

    # Human-readable narrative of what was found, including cross-tool
    # relationships (this is where "combining tools" actually shows value).
    if prime:
        findings.append(f"{n} is PRIME.")
        if mersenne:
            p = n.bit_length()  # n = 2^p - 1 has exactly p bits, all set to 1
            findings.append(
                f"{n} is also a MERSENNE PRIME (2^{p} - 1) — related to the OPEN question "
                f"of whether infinitely many Mersenne primes exist."
            )
        if twin_prime_partner:
            findings.append(f"{n} forms a TWIN PRIME pair with {twin_prime_partner}.")
    else:
        findings.append(f"{n} is composite. Prime factorization: {' x '.join(map(str, factors))}.")

    if perfect:
        findings.append(
            f"{n} is a PERFECT NUMBER (its proper divisors sum to itself) — related to the "
            f"OPEN 'odd perfect number' question (none has ever been found)."
        )
        # Euclid-Euler connection: every even perfect number = 2^(p-1) * (2^p - 1)
        # where 2^p - 1 is a Mersenne prime. Show this decomposition if it fits.
        largest_factor = max(factors) if factors else None
        if largest_factor and _is_mersenne_prime(largest_factor):
            findings.append(
                f"Euclid-Euler connection confirmed: {n} = 2^k x {largest_factor}, and "
                f"{largest_factor} is a Mersenne prime — exactly the known structure of every "
                f"even perfect number."
            )

    result = {
        "status": "ok",
        "n": n,
        "is_prime": prime,
        "prime_factors": factors,
        "is_perfect_number": perfect,
        "is_mersenne_prime": mersenne,
        "twin_prime_partner": twin_prime_partner,
        "findings": findings,
    }

    if include_oeis:
        # Best-effort — a real network call, degrades gracefully offline.
        oeis_result = lookup_sequence(str(n))
        result["oeis"] = oeis_result

    return result
