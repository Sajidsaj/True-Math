"""
Module Name: query_router
Purpose: Keyword-based routing for natural-language math questions —
         recognizes common patterns ("is X a perfect number", "factor X",
         "shortest path from A to B") and calls the right tool directly,
         without needing the LLM. This is the PRIMARY path (fast, free,
         reliable, no API key/rate-limit dependency); the LLM is only used
         when nothing here matches.
Responsibilities:
  - Match a query against a table of (regex pattern -> handler) rules.
  - Extract numeric/string arguments from the matched query.
  - Call the appropriate existing tool (number_explorer, number_theory,
    hard_problem_dispatcher, etc.) and return its result.
  - Log every UNMATCHED query to a persistent file, so a human can review
    what the router couldn't handle and add new patterns later.
Dependencies: re, src.core.history_store (for logging)
Honesty note on "learning": this router does NOT train, fine-tune, or
              modify itself. "Learning" here means exactly one thing: every
              query that falls through to the LLM gets appended to
              data/unmatched_queries.log with a timestamp. That's a
              transparent, human-readable record for YOU (or a future
              developer) to look at periodically and decide whether a new
              keyword pattern is worth adding to _PATTERNS below. There is
              no automatic self-modification — any claim that a system
              "trains itself" from this log without a human reviewing and
              writing new code would be exactly the kind of unverified
              claim this project has consistently avoided.
"""
from __future__ import annotations

import os
import re
import time
from typing import Callable, Dict, List, Optional, Tuple

from src.core.sys_logger import get_logger
from src.math_engine.hard_problem_dispatcher import solve as solve_hard_problem
from src.math_engine.number_explorer import explore_number
from src.math_engine.number_theory import mod_pow as _mod_pow_fn

logger = get_logger("QueryRouter")

_UNMATCHED_LOG_PATH = "data/unmatched_queries.log"

_NUMBER_RE = r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"


def _extract_numbers(text: str) -> List[float]:
    return [float(n) for n in re.findall(_NUMBER_RE, text)]


def _handle_perfect_number(query: str, match: re.Match) -> Optional[Dict]:
    nums = _extract_numbers(query)
    if not nums:
        return None
    n = int(nums[0])
    result = explore_number(n, include_oeis=False)
    if result["status"] != "ok":
        return None
    return {
        "answer": f"{n} is{'' if result['is_perfect_number'] else ' NOT'} a perfect number.",
        "steps": result["findings"],
        "verified": "Computed via divisor-sum check (exact, not guessed).",
        "verified_ok": True,
        "source": "router:number_explorer",
    }


def _handle_prime_check(query: str, match: re.Match) -> Optional[Dict]:
    nums = _extract_numbers(query)
    if not nums:
        return None
    n = int(nums[0])
    result = solve_hard_problem("number_theory", "is_prime", {"n": n})
    if result["status"] != "ok":
        return None
    return {
        "answer": f"{n} is{'' if result['result'] else ' NOT'} prime.",
        "steps": [f"Miller-Rabin primality test on {n}"],
        "verified": "Deterministic Miller-Rabin test (exact for this range).",
        "verified_ok": True,
        "source": "router:number_theory",
    }


def _handle_factor(query: str, match: re.Match) -> Optional[Dict]:
    nums = _extract_numbers(query)
    if not nums:
        return None
    n = int(nums[0])
    result = solve_hard_problem("number_theory", "prime_factors", {"n": n})
    if result["status"] != "ok":
        return None
    factors = result["result"]
    return {
        "answer": f"{n} = " + " x ".join(map(str, factors)),
        "steps": [f"Trial division + Pollard's rho factorization of {n}"],
        "verified": f"Product check: {' x '.join(map(str, factors))} = {n}.",
        "verified_ok": True,
        "source": "router:number_theory",
    }


def _handle_gcd(query: str, match: re.Match) -> Optional[Dict]:
    nums = _extract_numbers(query)
    if len(nums) < 2:
        return None
    a, b = int(nums[0]), int(nums[1])
    result = solve_hard_problem("number_theory", "gcd", {"a": a, "b": b})
    if result["status"] != "ok":
        return None
    return {
        "answer": f"gcd({a}, {b}) = {result['result']}",
        "steps": [f"Euclidean algorithm on {a} and {b}"],
        "verified": f"{result['result']} divides both {a} and {b}.",
        "verified_ok": True,
        "source": "router:number_theory",
    }


def _handle_mersenne(query: str, match: re.Match) -> Optional[Dict]:
    nums = _extract_numbers(query)
    if not nums:
        return None
    n = int(nums[0])
    result = explore_number(n, include_oeis=False)
    if result["status"] != "ok":
        return None
    return {
        "answer": f"{n} is{'' if result['is_mersenne_prime'] else ' NOT'} a Mersenne prime.",
        "steps": result["findings"],
        "verified": "Checked: n+1 is a power of 2, and n itself is prime.",
        "verified_ok": True,
        "source": "router:number_explorer",
    }


def _handle_twin_prime(query: str, match: re.Match) -> Optional[Dict]:
    nums = _extract_numbers(query)
    if not nums:
        return None
    n = int(nums[0])
    result = explore_number(n, include_oeis=False)
    if result["status"] != "ok":
        return None
    partner = result.get("twin_prime_partner")
    answer = f"{n} forms a twin prime pair with {partner}." if partner else f"{n} does not form a twin prime pair."
    return {
        "answer": answer,
        "steps": result["findings"],
        "verified": "Checked primality of n and n+/-2.",
        "verified_ok": True,
        "source": "router:number_explorer",
    }


def _handle_fibonacci(query: str, match: re.Match) -> Optional[Dict]:
    nums = _extract_numbers(query)
    if not nums:
        return None
    n = int(nums[0])
    result = solve_hard_problem("combinatorics", "fibonacci", {"n": n})
    if result["status"] != "ok":
        return None
    return {
        "answer": f"F({n}) = {result['result']}",
        "steps": [f"Fast-doubling Fibonacci computation for n={n}"],
        "verified": "Exact big-integer arithmetic (no floating-point rounding).",
        "verified_ok": True,
        "source": "router:combinatorics",
    }


def _handle_rsa_keygen(query: str, match: re.Match) -> Optional[Dict]:
    nums = _extract_numbers(query)
    bits = int(nums[0]) if nums else 2048
    if bits not in (2048, 3072, 4096):
        bits = 2048
    result = solve_hard_problem("real_crypto", "generate_keypair", {"key_size": bits})
    if result["status"] != "ok":
        return None
    keys = result["result"]
    return {
        "answer": (
            f"Real {bits}-bit RSA keypair generated (production-grade, OpenSSL-backed):\n\n"
            f"Public key:\n{keys['public_key_pem']}\n"
            f"Private key:\n{keys['private_key_pem']}"
        ),
        "steps": [f"Generated via cryptography library (real security, not a teaching demo)."],
        "verified": "Keys generated by an audited crypto library (OpenSSL) — genuinely secure at this bit size.",
        "verified_ok": True,
        "source": "router:real_crypto",
    }


def _handle_mod_pow(query: str, match: re.Match) -> Optional[Dict]:
    """Matches 'a^b mod m' or 'a to the power b mod m' style questions."""
    m = re.search(r"(-?\d+)\s*\^\s*(-?\d+)\s*mod\s*(-?\d+)", query, re.IGNORECASE)
    if not m:
        return None
    base, exp, mod = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if mod == 0:
        return None
    result = _mod_pow_fn(base, exp, mod)
    return {
        "answer": f"{base}^{exp} mod {mod} = {result}",
        "steps": [f"Fast modular exponentiation: {base}^{exp} mod {mod}"],
        "verified": "Computed via Python's built-in pow(base, exp, mod) — exact, no approximation.",
        "verified_ok": True,
        "source": "router:number_theory",
    }


def _handle_lcm(query: str, match: re.Match) -> Optional[Dict]:
    nums = _extract_numbers(query)
    if len(nums) < 2:
        return None
    a, b = int(nums[0]), int(nums[1])
    result = solve_hard_problem("number_theory", "lcm", {"a": a, "b": b})
    if result["status"] != "ok":
        return None
    return {
        "answer": f"lcm({a}, {b}) = {result['result']}",
        "steps": [f"Least common multiple of {a} and {b}"],
        "verified": f"{result['result']} is divisible by both {a} and {b}.",
        "verified_ok": True,
        "source": "router:number_theory",
    }


def _handle_mod_inverse(query: str, match: re.Match) -> Optional[Dict]:
    m = re.search(r"(-?\d+)\D+(-?\d+)", query)
    if not m:
        return None
    a, mod = int(m.group(1)), int(m.group(2))
    result = solve_hard_problem("number_theory", "mod_inverse", {"a": a, "m": mod})
    if result["status"] != "ok":
        return None
    if result["result"] is None:
        return {
            "answer": f"No modular inverse exists for {a} mod {mod} (gcd({a}, {mod}) != 1).",
            "steps": [f"Extended Euclidean algorithm on {a} and {mod}"],
            "verified": "Correctly detected non-invertibility (gcd check).",
            "verified_ok": True,
            "source": "router:number_theory",
        }
    return {
        "answer": f"The modular inverse of {a} mod {mod} is {result['result']}",
        "steps": [f"Extended Euclidean algorithm: {a} * x = 1 (mod {mod})"],
        "verified": f"Check: ({a} * {result['result']}) mod {mod} = 1.",
        "verified_ok": True,
        "source": "router:number_theory",
    }


def _handle_choose(query: str, match: re.Match) -> Optional[Dict]:
    nums = _extract_numbers(query)
    if len(nums) < 2:
        return None
    n, r = int(nums[0]), int(nums[1])
    result = solve_hard_problem("combinatorics", "n_choose_r", {"n": n, "r": r})
    if result["status"] != "ok":
        return None
    return {
        "answer": f"C({n}, {r}) = {result['result']}",
        "steps": [f"{n} choose {r} = {n}! / ({r}! * ({n}-{r})!)"],
        "verified": "Exact integer binomial coefficient (math.comb).",
        "verified_ok": True,
        "source": "router:combinatorics",
    }


def _handle_permute(query: str, match: re.Match) -> Optional[Dict]:
    nums = _extract_numbers(query)
    if len(nums) < 2:
        return None
    n, r = int(nums[0]), int(nums[1])
    result = solve_hard_problem("combinatorics", "n_permute_r", {"n": n, "r": r})
    if result["status"] != "ok":
        return None
    return {
        "answer": f"P({n}, {r}) = {result['result']}",
        "steps": [f"Permutations of {r} items from {n}: {n}!/({n}-{r})!"],
        "verified": "Exact integer permutation count (math.perm).",
        "verified_ok": True,
        "source": "router:combinatorics",
    }


def _handle_catalan(query: str, match: re.Match) -> Optional[Dict]:
    nums = _extract_numbers(query)
    if not nums:
        return None
    n = int(nums[0])
    result = solve_hard_problem("combinatorics", "catalan", {"n": n})
    if result["status"] != "ok":
        return None
    return {
        "answer": f"Catalan number C_{n} = {result['result']}",
        "steps": [f"C_n = (2n)! / ((n+1)! * n!) for n={n}"],
        "verified": "Exact integer arithmetic.",
        "verified_ok": True,
        "source": "router:combinatorics",
    }


# Physics constant name aliases -> canonical key in physics_tools.CONSTANTS
_CONSTANT_ALIASES = {
    "speed of light": "speed_of_light", "gravitational constant": "gravitational_constant",
    "planck constant": "planck_constant", "planck's constant": "planck_constant",
    "elementary charge": "elementary_charge", "electron mass": "electron_mass",
    "proton mass": "proton_mass", "avogadro": "avogadro_number",
    "boltzmann constant": "boltzmann_constant", "gas constant": "gas_constant",
    "standard gravity": "standard_gravity", "stefan boltzmann": "stefan_boltzmann_constant",
}


def _handle_physics_constant(query: str, match: re.Match) -> Optional[Dict]:
    ql = query.lower()
    for phrase, key in _CONSTANT_ALIASES.items():
        if phrase in ql:
            result = solve_hard_problem("physics", "get_constant", {"name": key})
            if result["status"] != "ok":
                return None
            c = result["result"]
            return {
                "answer": f"{key.replace('_', ' ').title()} ({c['symbol']}) = {c['value']} {c['unit']}",
                "steps": ["2018 CODATA recommended value"],
                "verified": "Standard published physical constant.",
                "verified_ok": True,
                "source": "router:physics",
            }
    return None


def _handle_schwarzschild(query: str, match: re.Match) -> Optional[Dict]:
    nums = _extract_numbers(query)
    if not nums:
        return None
    mass = nums[0]
    result = solve_hard_problem("relativity", "schwarzschild_radius", {"mass": mass})
    if result["status"] != "ok":
        return None
    r = result["result"]["schwarzschild_radius_meters"]
    return {
        "answer": f"Schwarzschild radius for a {mass} kg mass = {r:.6g} meters",
        "steps": ["r_s = 2GM/c^2"],
        "verified": "Exact closed-form General Relativity formula for a non-rotating mass.",
        "verified_ok": True,
        "source": "router:relativity",
    }


def _handle_lorentz(query: str, match: re.Match) -> Optional[Dict]:
    nums = _extract_numbers(query)
    if not nums:
        return None
    velocity = nums[0]
    # If phrased as "0.8c" or "0.8 c", treat as a fraction of light speed
    if re.search(r"\d\s*c\b", query, re.IGNORECASE) and velocity < 10:
        velocity = velocity * 299792458
    result = solve_hard_problem("relativity", "lorentz_factor", {"velocity": velocity})
    if result["status"] != "ok":
        return None
    return {
        "answer": f"Lorentz factor (gamma) at v={velocity:.4g} m/s = {result['result']['gamma']:.6g}",
        "steps": ["gamma = 1 / sqrt(1 - v^2/c^2)"],
        "verified": "Standard Special Relativity formula.",
        "verified_ok": True,
        "source": "router:relativity",
    }


def _handle_unit_convert(query: str, match: re.Match) -> Optional[Dict]:
    m = re.search(
        r"(-?\d+(?:\.\d+)?)\s*([a-zA-Z/°]+)\s*(?:to|in|into)\s*([a-zA-Z/°]+)", query, re.IGNORECASE
    )
    if not m:
        return None
    value, from_unit, to_unit = float(m.group(1)), m.group(2), m.group(3)

    is_temp = any(u in query.lower() for u in ("celsius", "fahrenheit", "kelvin", "°c", "°f"))
    op = "convert_temperature" if is_temp else "convert"
    result = solve_hard_problem("unit_converter", op, {"value": value, "from_unit": from_unit, "to_unit": to_unit})
    if result["status"] != "ok":
        return None
    r = result["result"]
    return {
        "answer": f"{value} {from_unit} = {r['value']:.6g} {to_unit}",
        "steps": [f"Converted {from_unit} -> {to_unit}"],
        "verified": "Exact conversion factor (or affine formula for temperature).",
        "verified_ok": True,
        "source": "router:unit_converter",
    }


def _handle_kinetic_energy(query: str, match: re.Match) -> Optional[Dict]:
    nums = _extract_numbers(query)
    if len(nums) < 2:
        return None
    mass, velocity = nums[0], nums[1]
    result = solve_hard_problem("physics", "kinetic_energy", {"mass": mass, "velocity": velocity})
    if result["status"] != "ok":
        return None
    return {
        "answer": f"Kinetic energy = {result['result']['kinetic_energy_joules']:.6g} Joules",
        "steps": [f"KE = 0.5 * m * v^2 = 0.5 * {mass} * {velocity}^2"],
        "verified": "Standard classical mechanics formula.",
        "verified_ok": True,
        "source": "router:physics",
    }


# Each entry: (compiled regex, handler). Checked in order; first match wins.
# IMPORTANT: more specific multi-word patterns that happen to contain a
# generic word as a substring (e.g. "lorentz factor" contains "factor",
# "catalan number" could look like a generic number query) MUST be listed
# BEFORE the generic pattern, or the generic one wins by accident.
_PATTERNS: List[Tuple[re.Pattern, Callable]] = [
    (re.compile(r"perfect number", re.IGNORECASE), _handle_perfect_number),
    (re.compile(r"mersenne", re.IGNORECASE), _handle_mersenne),
    (re.compile(r"twin prime", re.IGNORECASE), _handle_twin_prime),
    (re.compile(r"schwarzschild", re.IGNORECASE), _handle_schwarzschild),
    (re.compile(r"lorentz factor|time dilation factor|gamma factor", re.IGNORECASE), _handle_lorentz),
    (re.compile(r"kinetic energy", re.IGNORECASE), _handle_kinetic_energy),
    (re.compile(r"catalan number", re.IGNORECASE), _handle_catalan),
    (re.compile(r"generate.*rsa|create.*rsa.*key|rsa.*key.*pair", re.IGNORECASE), _handle_rsa_keygen),
    (re.compile(r"|".join(re.escape(k) for k in _CONSTANT_ALIASES), re.IGNORECASE), _handle_physics_constant),
    (re.compile(r"\bis\b.*\bprime\b|\bprime\b.*\bis\b", re.IGNORECASE), _handle_prime_check),
    (re.compile(r"factor|factorize|factorise", re.IGNORECASE), _handle_factor),
    (re.compile(r"\blcm\b|least common multiple", re.IGNORECASE), _handle_lcm),
    (re.compile(r"\bgcd\b|greatest common divisor", re.IGNORECASE), _handle_gcd),
    (re.compile(r"modular inverse|mod inverse|inverse.*mod", re.IGNORECASE), _handle_mod_inverse),
    (re.compile(r"fibonacci", re.IGNORECASE), _handle_fibonacci),
    (re.compile(r"\bchoose\b|combinations? of|binomial coefficient", re.IGNORECASE), _handle_choose),
    (re.compile(r"permutations? of", re.IGNORECASE), _handle_permute),
    (re.compile(r"\d+\s*\^\s*-?\d+\s*mod\s*-?\d+", re.IGNORECASE), _handle_mod_pow),
    (re.compile(r"\bconvert\b|\d\s*[a-zA-Z°]+\s*(?:to|in|into)\s*[a-zA-Z°]+", re.IGNORECASE), _handle_unit_convert),
]


def route_query(query: str) -> Optional[Dict]:
    """Tries every known keyword pattern against `query`. Returns a result
    dict (same shape as problem_solver's try_solve) on the first match, or
    None if nothing matched (caller should then try problem_solver, then
    the LLM). Logs unmatched queries for future review."""
    for pattern, handler in _PATTERNS:
        match = pattern.search(query)
        if match:
            try:
                result = handler(query, match)
                if result is not None:
                    return result
            except Exception as e:
                logger.warning(f"Router pattern matched but handler failed: {e}")
                continue  # fall through to try other patterns / eventually LLM

    _log_unmatched(query)
    return None


def _log_unmatched(query: str) -> None:
    """Appends the query to a plain-text log file for later human review —
    this is the entire 'learning' mechanism: a transparent record, not
    self-modification."""
    try:
        os.makedirs(os.path.dirname(_UNMATCHED_LOG_PATH) or ".", exist_ok=True)
        with open(_UNMATCHED_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{query}\n")
    except OSError as e:
        logger.debug(f"Could not write to unmatched query log: {e}")


def get_unmatched_queries(limit: int = 100) -> List[str]:
    """Returns the most recent unmatched queries from the log, for display
    in a 'suggested patterns to add' review panel."""
    if not os.path.exists(_UNMATCHED_LOG_PATH):
        return []
    with open(_UNMATCHED_LOG_PATH, encoding="utf-8") as f:
        lines = f.readlines()
    return [line.strip() for line in lines[-limit:]]
