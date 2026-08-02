"""
Module Name: differential_equations
Purpose: Real ordinary differential equation (ODE) solving using SymPy's
         dsolve — exact symbolic solutions, not numerical approximations.
Dependencies: sympy
Honesty note: dsolve can solve a wide range of standard ODE types (linear,
              separable, exact, several nonlinear forms) but not every ODE
              has a closed-form solution — some genuinely don't, and SymPy
              will say so rather than returning a wrong answer.
"""
from __future__ import annotations

from typing import Dict, Optional

import sympy
from sympy import Function, dsolve, Eq, symbols
from src.math_engine.safe_expr_parser import validate_safe_expression, UnsafeExpressionError
from sympy.parsing.sympy_parser import (
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

import re

x = symbols("x")
y = Function("y")

_TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application,)


def _build_safe_globals():
    """See safe_expr_parser.py module docstring for why this is necessary
    — blocks Python's automatic __builtins__ injection into eval()'d code."""
    safe_globals = {}
    safe_globals.update(vars(sympy))
    safe_globals["__builtins__"] = {}
    return safe_globals


_SAFE_GLOBALS = _build_safe_globals()


def _translate_ode_notation(equation_str: str) -> str:
    """Converts informal y', y'' notation into explicit SymPy Derivative(...)
    calls, and any remaining bare `y` into `y(x)` — done via regex passes so
    order/overlap issues (e.g. a leftover bare 'y' after handling y') can't
    silently produce a malformed expression."""
    s = equation_str
    s = re.sub(r"y''", "Derivative(y(x), x, x)", s)
    s = re.sub(r"y'(?!')", "Derivative(y(x), x)", s)
    # Any remaining standalone `y` (not already part of `y(` or `Derivative`) is the function itself.
    s = re.sub(r"\by\b(?!\()", "y(x)", s)
    return s


def solve_ode(equation_str: str, ics: Optional[Dict] = None) -> Dict:
    """Solves an ODE given as a string using y for the function and x for
    the variable, with derivatives written as y' , y'' (SymPy Derivative
    notation is built via .diff internally). Example inputs:
      "y' - y"              (solves y' = y  ->  y = C1*exp(x))
      "y'' + y"              (solves y'' = -y -> y = C1*sin(x) + C2*cos(x))
    Optional `ics` (initial conditions), e.g. {"y(0)": 1} to pin down the
    constants.
    """
    try:
        expr_str = _translate_ode_notation(equation_str)
        validate_safe_expression(expr_str)  # raises UnsafeExpressionError if unsafe

        local_dict = {"y": y, "x": x, "Derivative": sympy.Derivative}
        lhs = parse_expr(expr_str, local_dict=local_dict, global_dict=_SAFE_GLOBALS, transformations=_TRANSFORMATIONS)
        equation = Eq(lhs, 0)

        ics_parsed = None
        if ics:
            ics_parsed = {}
            for key, val in ics.items():
                validate_safe_expression(key)
                parsed_key = parse_expr(key, local_dict=local_dict, global_dict=_SAFE_GLOBALS, transformations=_TRANSFORMATIONS)
                if isinstance(val, str):
                    validate_safe_expression(val)
                ics_parsed[parsed_key] = sympy.sympify(val, evaluate=True) if not isinstance(val, str) else parse_expr(
                    val, local_dict=local_dict, global_dict=_SAFE_GLOBALS, transformations=_TRANSFORMATIONS
                )

        solution = dsolve(equation, y(x), ics=ics_parsed) if ics_parsed else dsolve(equation, y(x))
        return {"status": "ok", "equation": str(equation), "solution": str(solution)}
    except UnsafeExpressionError as e:
        return {"status": "error", "message": f"Unsafe expression rejected: {e}"}
    except NotImplementedError:
        return {"status": "error", "message": "This ODE type isn't solvable by SymPy's dsolve (no built-in method found)."}
    except Exception as e:
        return {"status": "error", "message": f"{type(e).__name__}: {e}"}
