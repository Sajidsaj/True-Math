"""
Module Name: lean4_translator
Purpose: Translate the internal Python/SymPy-flavored hypothesis strings
         (e.g. "x**2 + sin(x)") into syntactically VALID Lean 4 source code.
Responsibilities:
  - Convert Python operators (** -> ^) and function names (sin -> Real.sin,
    etc.) into their Lean 4 / Mathlib equivalents.
  - Decide whether the expression needs Mathlib (any transcendental
    function or π) or can be checked with bare Lean 4 core over integers.
Dependencies: re
Honesty note: This produces a syntactically well-typed Lean 4 EXPRESSION,
              not a proposition. Passing this check means "this is valid,
              well-typed mathematics" — it does NOT mean "this is a true
              theorem", because the hypothesis strings from the cognitive
              engine are bare expressions (e.g. "x^2 + sin(x)"), not
              equalities/inequalities to prove. Genuinely proving a
              conjecture would require generating a PROPOSITION plus a
              proof tactic, which is a materially harder problem this
              module does not attempt to solve.
"""
from __future__ import annotations

import re
from typing import Tuple

_MATHLIB_FUNCS = {
    "sin": "Real.sin",
    "cos": "Real.cos",
    "tan": "Real.tan",
    "exp": "Real.exp",
    "log": "Real.log",
    "sqrt": "Real.sqrt",
}


def translate_expression(expr_str: str) -> Tuple[str, bool]:
    """Returns (lean_expr, needs_mathlib)."""
    lean_expr = expr_str.replace("**", "^")
    needs_mathlib = False

    for py_name, lean_name in _MATHLIB_FUNCS.items():
        pattern = rf"\b{py_name}\("
        if re.search(pattern, lean_expr):
            lean_expr = re.sub(pattern, f"{lean_name}(", lean_expr)
            needs_mathlib = True

    if re.search(r"\bpi\b", lean_expr):
        lean_expr = re.sub(r"\bpi\b", "Real.pi", lean_expr)
        needs_mathlib = True
    if re.search(r"\bE\b", lean_expr):
        lean_expr = re.sub(r"\bE\b", "Real.exp 1", lean_expr)
        needs_mathlib = True

    return lean_expr, needs_mathlib


def build_lean_source(expr_str: str) -> Tuple[str, bool]:
    """Builds a complete, syntactically-valid Lean 4 source file body that
    type-checks the given expression. Returns (source, needs_mathlib) —
    the caller should only attempt to run this through `lake env lean` (not
    bare `lean`) when needs_mathlib is True, since bare Lean 4 doesn't
    have Real/trig functions without the Mathlib import."""
    lean_expr, needs_mathlib = translate_expression(expr_str)

    if needs_mathlib:
        source = (
            "-- TrueMath auto-generated (requires Mathlib)\n"
            "import Mathlib\n"
            "open Real\n\n"
            f"noncomputable example (x y z : ℝ) : ℝ := {lean_expr}\n"
        )
    else:
        # Pure integer arithmetic — checkable with bare `lean`, no Mathlib needed.
        source = (
            "-- TrueMath auto-generated (core Lean 4, no Mathlib needed)\n"
            f"example (x y z : ℤ) : ℤ := {lean_expr}\n"
        )

    return source, needs_mathlib
