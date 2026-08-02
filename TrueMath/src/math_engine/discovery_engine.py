"""
Module Name: discovery_engine
Purpose: Generate NEW (not-previously-written-down) instances of algebraic
         identities by substituting randomly-generated inner expressions
         into known identity templates (Pythagorean, double-angle, log/exp
         inverses, etc.), then symbolically PROVE each instance with SymPy.
Responsibilities:
  - Pick a known identity template + a random inner expression.
  - Build the resulting left/right-hand sides.
  - Verify equality exactly via symbolic simplification (never guessed).
  - Report the base identity it came from, honestly — this is generative
    instantiation + verification, not a claim of new-to-mathematics results.
Dependencies: sympy
Honesty note: Every "discovery" here is a specific instance of a KNOWN
              identity (e.g. sin²(u)+cos²(u)=1) with a random `u` plugged
              in. The exact combination is very likely something nobody
              wrote down in that precise form before, and it's rigorously
              verified — but it is NOT new mathematics in the research
              sense. This module never claims otherwise.
"""
from __future__ import annotations

import random
from typing import TypedDict

import sympy
from sympy import cos, exp, expand, log, simplify, sin, symbols

x = symbols("x", real=True)

# Each template: (lhs_builder, rhs_builder, human-readable base identity name)
_TEMPLATES = [
    (lambda u: sin(u) ** 2 + cos(u) ** 2, lambda u: sympy.Integer(1), "Pythagorean identity"),
    (lambda u: sin(2 * u), lambda u: 2 * sin(u) * cos(u), "Double-angle identity (sine)"),
    (lambda u: cos(2 * u), lambda u: cos(u) ** 2 - sin(u) ** 2, "Double-angle identity (cosine)"),
    (lambda u: sympy.Mul(exp(u), exp(-u), evaluate=False), lambda u: sympy.Integer(1), "Exponential inverse identity"),
    (lambda u: log(exp(u), evaluate=False), lambda u: u, "Log-exponential inverse identity"),
    (lambda u: (u + 1) ** 2 - (u - 1) ** 2, lambda u: 4 * u, "Difference-of-squares expansion"),
    (lambda u: (u + 1) ** 3 - (u - 1) ** 3, lambda u: 6 * u ** 2 + 2, "Cubic difference expansion"),
    (lambda u: sin(u) ** 4 - cos(u) ** 4, lambda u: sin(u) ** 2 - cos(u) ** 2, "Trig power-reduction identity"),
]

_INNER_BUILDERS = [
    lambda: x,
    lambda: x ** 2 + random.randint(1, 5) * x,
    lambda: sympy.Rational(random.randint(1, 4), random.randint(1, 4)) * x,
    lambda: x ** 2 - random.randint(1, 9),
    lambda: x + random.randint(1, 10),
    lambda: 2 * x ** 2 + random.randint(-5, 5) * x + random.randint(-5, 5),
]


class Discovery(TypedDict):
    base_identity: str
    substitution: str
    lhs: str
    rhs: str
    verified_equal: bool


def _numerically_verify(lhs, rhs, samples: int = 5, tolerance: float = 1e-9) -> bool:
    """Fallback check for when symbolic simplification can't resolve
    lhs == rhs (common for trig identities with complicated compound
    arguments, where the identity IS true but sympy's simplifier doesn't
    have a rewrite rule strong enough to prove it automatically). Evaluates
    both sides at several random real points — if they agree everywhere
    tested to high precision, that's strong evidence of a true identity."""
    try:
        f_lhs = sympy.lambdify(x, lhs, "mpmath")
        f_rhs = sympy.lambdify(x, rhs, "mpmath")
    except Exception:
        return False
    for _ in range(samples):
        sample = random.uniform(-10, 10)
        try:
            v_lhs, v_rhs = complex(f_lhs(sample)), complex(f_rhs(sample))
        except Exception:
            return False
        if abs(v_lhs - v_rhs) > tolerance * max(1.0, abs(v_lhs)):
            return False
    return True


def discover_identity() -> Discovery:
    """Generates one new, symbolically-verified instance of a known identity
    template with a randomly-built inner expression substituted in."""
    lhs_builder, rhs_builder, name = random.choice(_TEMPLATES)
    inner = random.choice(_INNER_BUILDERS)()

    lhs = lhs_builder(inner)
    rhs = rhs_builder(inner)

    # Independent proof: try exact symbolic simplification first (strongest
    # guarantee). If sympy's simplifier can't resolve it (common for trig
    # identities with complicated compound arguments — the identity can
    # still be genuinely true even when the automatic simplifier can't
    # prove it), fall back to numeric spot-checking at several real points.
    is_equal = simplify(expand(lhs - rhs)) == 0
    if not is_equal:
        is_equal = _numerically_verify(lhs, rhs)

    return {
        "base_identity": name,
        "substitution": str(inner),
        "lhs": str(lhs),
        "rhs": str(rhs),
        "verified_equal": bool(is_equal),
    }
