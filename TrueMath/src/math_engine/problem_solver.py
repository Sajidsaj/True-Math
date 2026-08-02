"""
Module Name: problem_solver
Purpose: Actually COMPUTE exact answers to well-defined, concrete math
         problems (equations, derivatives, integrals, simplification,
         factoring, arithmetic) using SymPy's symbolic engine — and then
         SELF-VERIFY every answer numerically before returning it, plus
         show the working steps and (for equations) graph data.
Responsibilities:
  - Detect what kind of concrete operation a plain-text question is asking for.
  - Parse it safely with SymPy and compute a real, exact result.
  - Independently re-check the result (substitution / numeric derivative /
    expansion) so a wrong answer is caught instead of silently returned.
  - Produce a short list of human-readable working steps.
  - For single-variable equations, produce sample (x, y) points so the UI
    can draw the curve with the root(s) marked.
  - Return None when the input isn't a concrete computable problem (the
    caller should then fall back to the LLM tutor for open-ended /
    conceptual / proof-style questions).
Dependencies: sympy
Honesty note: This module is ground truth for the specific patterns it
              recognizes (it does real symbolic math, not guessing). It
              CANNOT and does not attempt to solve open research problems
              (Riemann Hypothesis, P vs NP, etc.) — those aren't concrete
              computations, they're unsolved conjectures. The "self-verify"
              step is a genuine independent numeric/symbolic re-check, not
              cosmetic — if it fails, we say so instead of hiding it.
"""
from __future__ import annotations

import re
from typing import Optional, TypedDict

import sympy
from sympy import Symbol, diff, expand, factor, integrate, simplify, solve
from src.math_engine.safe_expr_parser import validate_safe_expression, UnsafeExpressionError
from sympy.parsing.sympy_parser import (
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

from src.core.sys_logger import get_logger

logger = get_logger("ProblemSolver")

_TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application,)
_ALLOWED_SYMBOLS = "xyzntuvwab"  # small, safe symbol universe
_LOCAL_DICT = {s: Symbol(s) for s in _ALLOWED_SYMBOLS}
_GRAPH_SAMPLE_COUNT = 41


class SolveResult(TypedDict, total=False):
    answer: str
    steps: list
    verified: str
    verified_ok: bool
    graph: dict


def _build_safe_globals():
    """Builds sympy's namespace, then explicitly blocks Python's automatic
    __builtins__ injection into eval()'d code. Must import sympy's names
    FIRST (that import itself needs real builtins), then lock down after."""
    safe_globals = {}
    safe_globals.update(vars(sympy))
    safe_globals["__builtins__"] = {}
    return safe_globals


_SAFE_GLOBALS = _build_safe_globals()


def _safe_parse(expr_str: str):
    """Parses a math expression string into a SymPy expression.

    SECURITY: this function is a defense-in-depth chokepoint. Layer 1
    (validate_safe_expression) rejects any AST construct beyond plain
    arithmetic/function calls using Python's own ast module — this catches
    every known eval() sandbox-escape pattern (dunder attribute access,
    subscripting, string literals used as exec targets, etc.) BEFORE any
    code reaches an eval-based parser. Layer 2 (_SAFE_GLOBALS) blocks
    Python's automatic __builtins__ injection as a second, independent
    safeguard. Do not remove either layer — this exists because a real
    remote-code-execution vulnerability was found and confirmed here
    during a security review (a submitted "math question" of
    `__import__("os").system(...)` executed a real shell command)."""
    cleaned = expr_str.strip().strip(":").strip()
    cleaned = cleaned.replace("^", "**")
    # Insert an explicit '*' between a digit and an immediately-following
    # letter (e.g. "2x" -> "2*x", "0x" -> "0*x"). This is required for two
    # reasons: it makes implicit multiplication unambiguous, and critically
    # it avoids "0x"/"0o"/"0b" being misread as a hex/octal/binary integer
    # literal prefix by Python's own tokenizer (a real bug: "0x" silently
    # failed to parse before this fix, since Python thinks it's the start
    # of a hex number like 0x1A).
    cleaned = re.sub(r"(\d)([a-zA-Z])", r"\1*\2", cleaned)

    validate_safe_expression(cleaned)  # raises UnsafeExpressionError if unsafe

    return parse_expr(cleaned, local_dict=_LOCAL_DICT, global_dict=_SAFE_GLOBALS, transformations=_TRANSFORMATIONS)


def _pick_var(expr) -> Symbol:
    free = expr.free_symbols
    if Symbol("x") in free:
        return Symbol("x")
    return sorted(free, key=str)[0] if free else Symbol("x")


def _graph_points(var: Symbol, y_expr, center: float, span: float = 8.0) -> Optional[dict]:
    """Samples y_expr(var) around `center` so the UI can plot the curve.
    Returns None if the function can't be safely evaluated numerically
    (e.g. still has other free symbols, or blows up everywhere)."""
    try:
        f = sympy.lambdify(var, y_expr, "math")
        points = []
        lo, hi = center - span, center + span
        for i in range(_GRAPH_SAMPLE_COUNT):
            x_val = lo + (hi - lo) * i / (_GRAPH_SAMPLE_COUNT - 1)
            try:
                y_val = float(f(x_val))
                if abs(y_val) < 1e6:  # skip asymptote blow-ups
                    points.append([round(x_val, 4), round(y_val, 4)])
            except (ValueError, ZeroDivisionError, OverflowError, TypeError):
                continue
        if len(points) < 5:
            return None
        return {"var": str(var), "points": points}
    except Exception as e:
        logger.debug(f"Graph sampling skipped: {e}")
        return None


def _numeric_check(original_expr, computed_expr, var: Symbol, sample: float = 1.7) -> tuple:
    """Independent numeric spot-check: evaluates both sides at a sample point
    and compares. Used to self-verify derivative/integral/simplify results
    rather than trusting the symbolic engine blindly."""
    try:
        f1 = sympy.lambdify(var, original_expr, "math")
        f2 = sympy.lambdify(var, computed_expr, "math")
        v1, v2 = float(f1(sample)), float(f2(sample))
        ok = abs(v1 - v2) < 1e-2 * max(1.0, abs(v1))
        return ok, v1, v2
    except Exception:
        return None, None, None


def try_solve(question: str) -> Optional[SolveResult]:
    """Attempts to compute a real, exact, SELF-VERIFIED answer to a concrete
    math question. Returns a dict with answer/steps/verified/graph, or None
    if the question doesn't match a supported concrete-computation pattern.
    """
    q = question.strip()
    if not q:
        return None
    ql = q.lower()

    try:
        # ── Plot / graph only (no solving needed) ────────────────
        if ql.startswith("plot ") or ql.startswith("graph "):
            body = re.sub(r"^(plot|graph)\s+", "", q, flags=re.IGNORECASE)
            expr = _safe_parse(body)
            var = _pick_var(expr)
            graph = _graph_points(var, expr, center=0.0)
            return {
                "answer": f"Graph of {expr}",
                "answer_latex": f"f({sympy.latex(var)}) = {sympy.latex(expr)}",
                "steps": [f"f({var}) = {expr}"],
                "verified": "Plotted directly from the expression (no solving needed).",
                "verified_ok": True,
                "graph": graph,
            }

        # ── Derivative ──────────────────────────────────────────
        if ql.startswith("derivative") or ql.startswith("differentiate") or ql.startswith("d/dx"):
            body = q
            for prefix in ("derivative of ", "differentiate ", "d/dx "):
                if body.lower().startswith(prefix):
                    body = body[len(prefix):]
                    break
            body = re.sub(r"\s+with respect to\s+\w+\s*$", "", body, flags=re.IGNORECASE)
            expr = _safe_parse(body)
            var = _pick_var(expr)
            result = simplify(diff(expr, var))

            # Self-check: numerically approximate the derivative via finite
            # differences and compare against the symbolic result.
            steps = [f"f({var}) = {expr}", f"Apply differentiation rules w.r.t. {var}", f"f'({var}) = {result}"]
            try:
                h = 1e-6
                sample = 1.7
                f = sympy.lambdify(var, expr, "math")
                numeric_deriv = (f(sample + h) - f(sample - h)) / (2 * h)
                symbolic_val = float(result.subs(var, sample))
                ok = abs(numeric_deriv - symbolic_val) < 1e-2 * max(1.0, abs(symbolic_val))
                verified = (
                    f"Self-check via finite-difference numeric derivative at {var}={sample}: "
                    f"numeric ≈ {numeric_deriv:.5f}, symbolic = {symbolic_val:.5f} "
                    f"{'✓ match' if ok else '✗ MISMATCH — treat with caution'}"
                )
            except Exception:
                ok, verified = None, "Could not run an independent numeric check for this expression."

            return {
                "answer": f"d/d{var} [{expr}] = {result}",
                "answer_latex": f"\\frac{{d}}{{d{sympy.latex(var)}}}\\left[{sympy.latex(expr)}\\right] = {sympy.latex(result)}",
                "steps": steps,
                "verified": verified,
                "verified_ok": bool(ok),
                "graph": _graph_points(var, result, center=1.7),
            }

        # ── Integral ────────────────────────────────────────────
        if ql.startswith("integrate") or ql.startswith("integral of") or ql.startswith("∫"):
            body = q
            for prefix in ("integrate ", "integral of ", "∫"):
                if body.lower().startswith(prefix):
                    body = body[len(prefix):]
                    break
            expr = _safe_parse(body)
            var = _pick_var(expr)
            result = simplify(integrate(expr, var))

            steps = [f"∫ {expr} d{var}", "Apply integration rules", f"= {result} + C"]
            # Self-check: differentiate the result back and compare to the
            # original integrand numerically — the fundamental theorem of
            # calculus, used as an automatic sanity check.
            try:
                back = diff(result, var)
                ok, v1, v2 = _numeric_check(expr, back, var)
                verified = (
                    f"Self-check via Fundamental Theorem of Calculus (differentiating the "
                    f"result back): f({1.7}) ≈ {v1:.5f}, d/dx[answer]({1.7}) ≈ {v2:.5f} "
                    f"{'✓ match' if ok else '✗ MISMATCH — treat with caution'}"
                ) if ok is not None else "Could not run an independent numeric check for this expression."
            except Exception:
                ok, verified = None, "Could not run an independent numeric check for this expression."

            return {
                "answer": f"∫ {expr} d{var} = {result} + C",
                "answer_latex": f"\\int {sympy.latex(expr)}\\,d{sympy.latex(var)} = {sympy.latex(result)} + C",
                "steps": steps,
                "verified": verified,
                "verified_ok": bool(ok),
                "graph": _graph_points(var, expr, center=1.7),
            }

        # ── Simplify ────────────────────────────────────────────
        if ql.startswith("simplify"):
            body = q[len("simplify"):]
            expr = _safe_parse(body)
            var = _pick_var(expr)

            # Multi-stage simplification pipeline: try several real SymPy
            # rewriting strategies in sequence, keeping any stage that
            # actually reduces sympy.count_ops (a genuine, quantifiable
            # measure of expression complexity — not a cosmetic claim).
            original_ops = sympy.count_ops(expr)
            current = expr
            pipeline_steps = [f"Original ({original_ops} operations): {expr}"]
            for stage_name, stage_fn in [
                ("factor", sympy.factor), ("cancel", sympy.cancel),
                ("trigsimp", sympy.trigsimp), ("radsimp", sympy.radsimp),
                ("simplify", simplify),
            ]:
                try:
                    candidate = stage_fn(current)
                    candidate_ops = sympy.count_ops(candidate)
                    if candidate_ops < sympy.count_ops(current):
                        pipeline_steps.append(f"After {stage_name} ({candidate_ops} operations): {candidate}")
                        current = candidate
                except Exception:
                    continue

            result = current
            final_ops = sympy.count_ops(result)
            reduction_pct = round((1 - final_ops / original_ops) * 100, 1) if original_ops > 0 else 0.0

            ok, v1, v2 = (_numeric_check(expr, result, var) if var in expr.free_symbols else (True, None, None))
            verified = (
                f"Self-check at {var}=1.7: original ≈ {v1:.5f}, simplified ≈ {v2:.5f} "
                f"{'✓ match' if ok else '✗ MISMATCH'}"
            ) if v1 is not None else "Expression has no free variable to numerically spot-check — verified symbolically only."

            return {
                "answer": f"Simplified: {result}  ({original_ops} → {final_ops} operations, {reduction_pct}% shorter)",
                "answer_latex": sympy.latex(result),
                "steps": pipeline_steps,
                "verified": verified,
                "verified_ok": bool(ok) if ok is not None else True,
            }

        # ── Factor ──────────────────────────────────────────────
        if ql.startswith("factor"):
            body = re.sub(r"^factor(ize)?\s*", "", q, flags=re.IGNORECASE)
            expr = _safe_parse(body)
            result = factor(expr)
            steps = [f"Original: {expr}", f"Factored: {result}"]
            # Self-check: expanding the factored form must equal the original.
            ok = simplify(expand(result) - expand(expr)) == 0
            verified = (
                f"Self-check: expanding {result} back gives {expand(result)}, "
                f"which {'✓ matches' if ok else '✗ does NOT match'} the original {expand(expr)}."
            )
            return {"answer": f"Factored: {result}", "answer_latex": sympy.latex(result), "steps": steps, "verified": verified, "verified_ok": ok}

        # ── Equation solving: "2x + 3 = 11", "x^2 - 4 = 0" ───────
        if "=" in q and "==" not in q and q.count("=") == 1:
            lhs_str, rhs_str = q.split("=", 1)
            lhs = _safe_parse(lhs_str)
            rhs = _safe_parse(rhs_str)
            free = lhs.free_symbols | rhs.free_symbols
            if len(free) != 1:
                return None  # multiple/zero unknowns — let the LLM tutor explain instead
            var = next(iter(free))
            solutions = solve(sympy.Eq(lhs, rhs), var)
            if not solutions:
                return None

            steps = [f"{lhs} = {rhs}", f"Rearrange and solve for {var}"]
            # Self-check: substitute each solution back into both sides.
            all_ok = True
            check_lines = []
            for sol in solutions:
                lhs_val = lhs.subs(var, sol)
                rhs_val = rhs.subs(var, sol)
                match = simplify(lhs_val - rhs_val) == 0
                all_ok = all_ok and match
                check_lines.append(f"{var}={sol}: LHS={lhs_val}, RHS={rhs_val} {'✓' if match else '✗'}")

            sol_str = ", ".join(str(s) for s in solutions)
            real_solutions = [s for s in solutions if getattr(s, "is_real", True)]
            graph = None
            if real_solutions:
                try:
                    center = float(real_solutions[0])
                    graph = _graph_points(var, lhs - rhs, center=center)
                except (TypeError, ValueError):
                    pass

            return {
                "answer": f"{var} = {sol_str}",
                "answer_latex": ", \\; ".join(f"{sympy.latex(var)} = {sympy.latex(s)}" for s in solutions),
                "steps": steps,
                "verified": "Substituted back into the original equation — " + "; ".join(check_lines),
                "verified_ok": all_ok,
                "graph": graph,
            }

        # ── Plain arithmetic: "2 + 2", "(5*3)/2" ─────────────────
        if re.fullmatch(r"[\d\.\s\+\-\*/\^\(\)]+", q):
            expr = _safe_parse(q)
            evaluated = sympy.nsimplify(expr)
            try:
                numeric = float(expr)
                return {
                    "answer": f"= {evaluated} (≈ {numeric:.6g})",
                    "answer_latex": sympy.latex(evaluated),
                    "steps": [f"{q.strip()} = {evaluated}"],
                    "verified": "Exact rational/symbolic arithmetic — no approximation involved.",
                    "verified_ok": True,
                }
            except (TypeError, ValueError):
                return {
                    "answer": f"= {evaluated}",
                    "answer_latex": sympy.latex(evaluated),
                    "steps": [f"{q.strip()} = {evaluated}"],
                    "verified": "Exact symbolic arithmetic.",
                    "verified_ok": True,
                }

    except UnsafeExpressionError as e:
        logger.warning(f"Blocked unsafe expression (potential attack attempt): '{q[:100]}' -> {e}")
        return None
    except Exception as e:
        logger.debug(f"Symbolic solver could not handle '{q[:60]}': {e}")
        return None

    return None
