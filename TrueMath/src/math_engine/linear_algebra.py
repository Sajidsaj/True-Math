"""
Module Name: linear_algebra
Purpose: Real matrix/linear-algebra operations using SymPy's exact rational
         arithmetic (not floating-point approximations) — determinant,
         inverse, eigenvalues/eigenvectors, and solving linear systems Ax=b.
Dependencies: sympy
Security note: All functions enforce a hard matrix-dimension cap
              (_MAX_MATRIX_DIM). Confirmed during a security review that a
              100x100 matrix (well within normal JSON payload size limits)
              takes 5+ seconds for a single exact-arithmetic determinant —
              a real CPU-exhaustion DoS vector against a publicly
              reachable server. 40x40 keeps worst-case latency under
              ~0.3s while comfortably covering legitimate use cases.
"""
from __future__ import annotations

from typing import Dict, List

import sympy
from sympy import Matrix

_MAX_MATRIX_DIM = 40


def _to_matrix(rows: List[List]) -> Matrix:
    return Matrix(rows)


def _check_dimensions(*matrices: Matrix) -> Dict:
    """Returns an error dict if any matrix exceeds the safe size cap, else
    an empty dict (falsy, so `if err := _check_dimensions(...): return err`
    reads naturally at each call site)."""
    for m in matrices:
        if m.rows > _MAX_MATRIX_DIM or m.cols > _MAX_MATRIX_DIM:
            return {
                "status": "error",
                "message": f"Matrix too large ({m.rows}x{m.cols}) — max {_MAX_MATRIX_DIM}x{_MAX_MATRIX_DIM} "
                           "(exact symbolic arithmetic gets very slow beyond this).",
            }
    return {}


def determinant(matrix: List[List]) -> Dict:
    m = _to_matrix(matrix)
    if err := _check_dimensions(m):
        return err
    if m.rows != m.cols:
        return {"status": "error", "message": f"Matrix must be square (got {m.rows}x{m.cols})."}
    return {"status": "ok", "determinant": str(m.det())}


def inverse(matrix: List[List]) -> Dict:
    m = _to_matrix(matrix)
    if err := _check_dimensions(m):
        return err
    if m.rows != m.cols:
        return {"status": "error", "message": f"Matrix must be square (got {m.rows}x{m.cols})."}
    if m.det() == 0:
        return {"status": "error", "message": "Matrix is singular (determinant = 0) — no inverse exists."}
    inv = m.inv()
    return {"status": "ok", "inverse": [[str(v) for v in row] for row in inv.tolist()]}


def eigenvalues(matrix: List[List]) -> Dict:
    m = _to_matrix(matrix)
    if err := _check_dimensions(m):
        return err
    if m.rows != m.cols:
        return {"status": "error", "message": f"Matrix must be square (got {m.rows}x{m.cols})."}
    eig_dict = m.eigenvals()  # {eigenvalue: multiplicity}
    eigs = [{"value": str(val), "multiplicity": mult} for val, mult in eig_dict.items()]
    return {"status": "ok", "eigenvalues": eigs}


def solve_linear_system(A: List[List], b: List) -> Dict:
    """Solves Ax = b exactly. Reports unique solution, or that the system is
    inconsistent/underdetermined (real, honest outcomes — not every system
    has a unique solution, and this says so rather than guessing)."""
    m = _to_matrix(A)
    b_vec = Matrix(b)
    if err := _check_dimensions(m, b_vec):
        return err
    if m.rows != b_vec.rows:
        return {"status": "error", "message": f"A has {m.rows} rows but b has {b_vec.rows} entries — must match."}

    augmented = m.row_join(b_vec)
    rank_A = m.rank()
    rank_aug = augmented.rank()

    if rank_A < rank_aug:
        return {"status": "ok", "solvable": False, "message": "No solution exists — the system is inconsistent."}
    if rank_A < m.cols:
        return {"status": "ok", "solvable": False, "message": f"Infinitely many solutions exist (rank {rank_A} < {m.cols} unknowns) — underdetermined system."}

    try:
        solution = m.solve(b_vec)
        return {"status": "ok", "solvable": True, "x": [str(v) for v in solution]}
    except Exception as e:
        return {"status": "error", "message": f"Could not solve: {e}"}


def matrix_multiply(A: List[List], B: List[List]) -> Dict:
    m1, m2 = _to_matrix(A), _to_matrix(B)
    if err := _check_dimensions(m1, m2):
        return err
    if m1.cols != m2.rows:
        return {"status": "error", "message": f"Cannot multiply {m1.rows}x{m1.cols} by {m2.rows}x{m2.cols} — inner dimensions must match."}
    result = m1 * m2
    return {"status": "ok", "result": [[str(v) for v in row] for row in result.tolist()]}


def rank(matrix: List[List]) -> Dict:
    m = _to_matrix(matrix)
    if err := _check_dimensions(m):
        return err
    return {"status": "ok", "rank": m.rank(), "shape": [m.rows, m.cols]}
