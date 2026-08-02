"""
Module Name: complexity_analyzer
Purpose: Estimates Big-O time complexity via real static-analysis
         techniques used by actual complexity tools/CS courses:
           1. Loop classification — distinguishes a normal O(n) loop from a
              logarithmic O(log n) loop (variable halved/divided each
              iteration, e.g. `while n > 1: n //= 2`).
           2. Recursion recurrence extraction — finds each recursive
              self-call, inspects its argument to detect whether the input
              shrinks by a constant DECREMENT (n-1, linear recursion) or a
              constant DIVISOR (n//2, divide-and-conquer), counts the
              branching factor (how many recursive calls per invocation),
              and applies the Master Theorem to combine that with the
              non-recursive work done per call.
         This is meaningfully more than counting nested loops — it's the
         same reasoning (recurrence relations + Master Theorem) taught in
         algorithms courses and used by real complexity-estimation tools.
Dependencies: ast (stdlib)
Honesty note: Determining the EXACT complexity of arbitrary code is
              undecidable in general (this follows from Rice's theorem) —
              no static tool, however sophisticated, can be complete and
              always-correct for arbitrary programs. This analyzer handles
              the common, well-defined patterns (simple loops, logarithmic
              loops, divide-and-conquer and linear recursion) that most
              textbook/interview code falls into, using real recurrence
              analysis rather than a naive heuristic — but it can still be
              fooled by unusual control flow, indirect recursion, or
              amortized-cost patterns. Treat it as a genuine analytical
              estimate, not an infallible guarantee.
"""
from __future__ import annotations

import ast
from typing import Dict, List, Optional, Tuple

# Well-known complexities of common built-ins, surfaced as extra info
# (not folded into the main estimate, since knowing they're called doesn't
# tell us how many times).
_BUILTIN_HINTS = {
    "sorted": "O(n log n)",
    "sort": "O(n log n)",
    "min": "O(n)", "max": "O(n)", "sum": "O(n)",
}


class _LoopInfo:
    def __init__(self, kind: str, depth: int):
        self.kind = kind  # "linear" or "logarithmic"
        self.depth = depth


class _FunctionAnalysis(ast.NodeVisitor):
    def __init__(self, func_name: str):
        self.func_name = func_name
        self.current_depth = 0
        self.loops: List[_LoopInfo] = []
        self.max_linear_depth = 0
        self.has_log_loop = False
        self.recursive_calls: List[ast.Call] = []
        self.builtin_hits: set = set()

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            if node.func.id == self.func_name:
                self.recursive_calls.append(node)
            elif node.func.id in _BUILTIN_HINTS:
                self.builtin_hits.add(node.func.id)
        elif isinstance(node.func, ast.Attribute) and node.func.attr in _BUILTIN_HINTS:
            self.builtin_hits.add(node.func.attr)
        self.generic_visit(node)

    def _is_logarithmic_while(self, node: ast.While) -> bool:
        """Detects the classic `while cond: var = var // 2` (or var /= 2,
        var >>= 1) pattern — the loop variable shrinks by a constant
        divisor each iteration, giving O(log n) iterations instead of O(n)."""
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.AugAssign) and isinstance(stmt.op, (ast.FloorDiv, ast.Div, ast.RShift)):
                return True
            if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.BinOp):
                if isinstance(stmt.value.op, (ast.FloorDiv, ast.Div, ast.RShift)):
                    return True
        return False

    def _visit_loop(self, node, kind: str):
        self.current_depth += 1
        self.loops.append(_LoopInfo(kind, self.current_depth))
        if kind == "logarithmic":
            self.has_log_loop = True
        else:
            self.max_linear_depth = max(self.max_linear_depth, self.current_depth)
        self.generic_visit(node)
        self.current_depth -= 1

    def visit_For(self, node: ast.For):
        self._visit_loop(node, "linear")

    def visit_While(self, node: ast.While):
        kind = "logarithmic" if self._is_logarithmic_while(node) else "linear"
        self._visit_loop(node, kind)


def _extract_reduction(call: ast.Call) -> Tuple[Optional[str], Optional[int]]:
    """Looks at ALL of a recursive call's arguments (the 'size' parameter
    isn't always first) to classify how the input shrinks: ('decrement', k)
    for arg-k, ('divide', b) for arg//b or arg/b, or (None, None) if no
    recognizable pattern is found in any argument."""
    for arg in call.args:
        if isinstance(arg, ast.BinOp):
            if isinstance(arg.op, ast.Sub) and isinstance(arg.right, ast.Constant):
                return "decrement", arg.right.value
            if isinstance(arg.op, (ast.FloorDiv, ast.Div)) and isinstance(arg.right, ast.Constant):
                return "divide", arg.right.value
    return None, None


def _non_recursive_work_degree(analysis: _FunctionAnalysis) -> int:
    """The polynomial degree of work done per call OUTSIDE the recursive
    calls themselves — i.e. the max nesting depth of plain (non-log) loops
    not counting recursion. Used as the Master Theorem's f(n) = O(n^d)."""
    return analysis.max_linear_depth


def _apply_master_theorem(a: int, b: int, d: int) -> str:
    """Master Theorem: T(n) = a*T(n/b) + O(n^d).
    Compares a to b^d to determine which term dominates."""
    b_pow_d = b ** d
    if a < b_pow_d:
        return f"O(n^{d})" if d > 0 else "O(1)"
    elif a == b_pow_d:
        return f"O(n^{d} log n)" if d > 0 else "O(log n)"
    else:
        # a > b^d: dominated by the recursion tree, exponent = log_b(a)
        import math
        exponent = math.log(a) / math.log(b)
        # Report as a clean fraction/int where it lands near one
        rounded = round(exponent, 3)
        return f"O(n^{rounded})"


def _classify_recursive(analysis: _FunctionAnalysis) -> str:
    a = len(analysis.recursive_calls)  # branching factor
    d = _non_recursive_work_degree(analysis)
    reductions = [_extract_reduction(c) for c in analysis.recursive_calls]
    kinds = {r[0] for r in reductions}

    if "divide" in kinds:
        # Divide-and-conquer: use the Master Theorem.
        b_values = [r[1] for r in reductions if r[0] == "divide" and r[1]]
        b = b_values[0] if b_values else 2
        complexity = _apply_master_theorem(a, b, d)
        return (
            f"{complexity} — divide-and-conquer recursion detected: {a} recursive call(s) each on "
            f"~n/{b} sized input, plus O(n^{d}) work per call (Master Theorem: a={a}, b={b}, d={d})."
        )

    if "decrement" in kinds or not kinds:
        # Linear-reduction recursion: T(n) = a*T(n-1) + O(n^d)
        if a <= 1:
            base_complexity = f"O(n^{d + 1})" if d > 0 else "O(n)"
            return (
                f"{base_complexity} — single recursive call reducing input by a constant each time "
                f"(like factorial-style recursion), with O(n^{d}) extra work per call."
            )
        else:
            return (
                f"O({a}^n) — {a} recursive calls per invocation, each reducing input by a constant "
                f"(branching recursion, like naive Fibonacci if a=2) — exponential growth dominates any "
                f"O(n^{d}) per-call work."
            )

    return "Recursive, but the argument pattern isn't a simple decrement/divide — inspect manually."


def _classify_iterative(analysis: _FunctionAnalysis) -> str:
    if analysis.max_linear_depth == 0 and not analysis.has_log_loop:
        return "O(1) — no loops or recursion detected (constant time, assuming no hidden complexity in called functions)"
    if analysis.max_linear_depth == 0 and analysis.has_log_loop:
        return "O(log n) — only logarithmic loop(s) detected (variable halved/divided each iteration)"
    if analysis.has_log_loop:
        return f"O(n^{analysis.max_linear_depth} log n) — {analysis.max_linear_depth} nested linear loop(s) plus a logarithmic loop"
    if analysis.max_linear_depth == 1:
        return "O(n) — single linear loop, no nesting"
    return f"O(n^{analysis.max_linear_depth}) — {analysis.max_linear_depth} nested linear loop(s)"


def analyze_complexity(code: str) -> Dict:
    """Parses Python source containing one or more function definitions and
    estimates each function's time complexity using loop classification
    (linear vs logarithmic) and, for recursive functions, recurrence
    extraction + the Master Theorem."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {"status": "error", "message": f"Python syntax error: {e}"}

    functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    if not functions:
        return {"status": "error", "message": "No function definitions found in the code."}

    results: List[Dict] = []
    for func_node in functions:
        analysis = _FunctionAnalysis(func_node.name)
        analysis.visit(func_node)

        is_recursive = len(analysis.recursive_calls) > 0
        estimate = _classify_recursive(analysis) if is_recursive else _classify_iterative(analysis)

        entry = {
            "function": func_node.name,
            "is_recursive": is_recursive,
            "max_linear_loop_depth": analysis.max_linear_depth,
            "has_logarithmic_loop": analysis.has_log_loop,
            "recursive_call_count": len(analysis.recursive_calls),
            "estimated_complexity": estimate,
        }
        if analysis.builtin_hits:
            entry["builtin_calls_detected"] = {name: _BUILTIN_HINTS[name] for name in analysis.builtin_hits}
        results.append(entry)

    return {"status": "ok", "functions": results}
