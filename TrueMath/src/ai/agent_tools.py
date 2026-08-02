"""
Module Name: agent_tools
Purpose: Defines tool schemas (OpenAI/Groq function-calling JSON format) so
         an LLM can be given real tools to call — including matrix/linear
         algebra operations — for compound questions that combine multiple
         sub-problems ("factor 360, then take its gcd with 48, then tell me
         the determinant of [[2,1],[1,3]]").
Responsibilities:
  - Define a curated set of tool schemas the LLM can choose from.
  - Execute a tool call by routing to the real hard_problem_dispatcher
    (the actual computation is ALWAYS done by verified Python code, never
    by the LLM itself — the LLM only decides WHICH tool to call and with
    what arguments).
Dependencies: src.math_engine.hard_problem_dispatcher
Honesty note: The LLM's role here is limited to ROUTING (deciding which
              real function to call, and parsing your question into that
              function's arguments) — it never performs the actual math.
              Every number in the final answer traces back to one of the
              already-tested, deterministic solvers in this project. If the
              LLM picks the wrong tool or extracts the wrong arguments, the
              tool's real (correct) result for THOSE arguments is still
              what gets returned — the failure mode is "wrong question
              answered correctly", not "right question answered wrongly by
              a hallucinating model".
"""
from __future__ import annotations

from typing import Any, Dict, List

from src.math_engine.hard_problem_dispatcher import solve as solve_hard_problem

# OpenAI/Groq function-calling tool schemas. Kept to a curated, high-value
# subset (matrix/linear algebra explicitly requested, plus broad coverage)
# rather than exhaustively wrapping all 50+ dispatcher operations — each
# schema needs to be clear enough for the model to fill in correctly.
TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "matrix_determinant",
            "description": "Computes the exact determinant of a square matrix.",
            "parameters": {
                "type": "object",
                "properties": {
                    "matrix": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "number"}},
                        "description": "A square matrix as a list of row lists, e.g. [[2,1],[1,3]]",
                    }
                },
                "required": ["matrix"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "matrix_inverse",
            "description": "Computes the exact inverse of a square matrix, if it exists.",
            "parameters": {
                "type": "object",
                "properties": {
                    "matrix": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "number"}},
                        "description": "A square matrix as a list of row lists.",
                    }
                },
                "required": ["matrix"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "matrix_solve_system",
            "description": "Solves the linear system Ax = b for x.",
            "parameters": {
                "type": "object",
                "properties": {
                    "A": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}},
                    "b": {"type": "array", "items": {"type": "number"}},
                },
                "required": ["A", "b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "matrix_eigenvalues",
            "description": "Computes the eigenvalues of a square matrix.",
            "parameters": {
                "type": "object",
                "properties": {
                    "matrix": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}}
                },
                "required": ["matrix"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "number_theory_gcd",
            "description": "Computes the greatest common divisor of two integers.",
            "parameters": {
                "type": "object",
                "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
                "required": ["a", "b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "number_theory_prime_factors",
            "description": "Computes the full prime factorization of a positive integer.",
            "parameters": {
                "type": "object",
                "properties": {"n": {"type": "integer"}},
                "required": ["n"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "number_theory_is_prime",
            "description": "Checks whether an integer is prime.",
            "parameters": {
                "type": "object",
                "properties": {"n": {"type": "integer"}},
                "required": ["n"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "explore_number",
            "description": "Runs a combined analysis of an integer: primality, factorization, perfect-number check, Mersenne/twin-prime relationships.",
            "parameters": {
                "type": "object",
                "properties": {"n": {"type": "integer"}},
                "required": ["n"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "unit_convert",
            "description": "Converts a numeric value between compatible physical units (length, mass, speed, energy, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {"type": "number"},
                    "from_unit": {"type": "string"},
                    "to_unit": {"type": "string"},
                },
                "required": ["value", "from_unit", "to_unit"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "physics_kinematics",
            "description": "Solves constant-acceleration kinematics (SUVAT): given any subset of u, v, a, t, s, solves for the rest.",
            "parameters": {
                "type": "object",
                "properties": {
                    "u": {"type": "number", "description": "initial velocity"},
                    "v": {"type": "number", "description": "final velocity"},
                    "a": {"type": "number", "description": "acceleration"},
                    "t": {"type": "number", "description": "time"},
                    "s": {"type": "number", "description": "displacement"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "relativity_schwarzschild_radius",
            "description": "Computes the Schwarzschild radius (event horizon) for a given mass in kg.",
            "parameters": {
                "type": "object",
                "properties": {"mass": {"type": "number"}},
                "required": ["mass"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "relativity_lorentz_factor",
            "description": "Computes the relativistic Lorentz factor (gamma) for a velocity in m/s.",
            "parameters": {
                "type": "object",
                "properties": {"velocity": {"type": "number"}},
                "required": ["velocity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "combinatorics_choose",
            "description": "Computes the binomial coefficient C(n, r) — 'n choose r'.",
            "parameters": {
                "type": "object",
                "properties": {"n": {"type": "integer"}, "r": {"type": "integer"}},
                "required": ["n", "r"],
            },
        },
    },
]

# Maps each tool name to (category, operation) in the real dispatcher, or a
# special local handler for tools that don't map 1:1 (like explore_number).
_TOOL_TO_DISPATCH = {
    "matrix_determinant": ("linear_algebra", "determinant", lambda a: {"matrix": a["matrix"]}),
    "matrix_inverse": ("linear_algebra", "inverse", lambda a: {"matrix": a["matrix"]}),
    "matrix_solve_system": ("linear_algebra", "solve_system", lambda a: {"A": a["A"], "b": a["b"]}),
    "matrix_eigenvalues": ("linear_algebra", "eigenvalues", lambda a: {"matrix": a["matrix"]}),
    "number_theory_gcd": ("number_theory", "gcd", lambda a: {"a": a["a"], "b": a["b"]}),
    "number_theory_prime_factors": ("number_theory", "prime_factors", lambda a: {"n": a["n"]}),
    "number_theory_is_prime": ("number_theory", "is_prime", lambda a: {"n": a["n"]}),
    "unit_convert": ("unit_converter", "convert", lambda a: a),
    "physics_kinematics": ("physics", "kinematics", lambda a: a),
    "relativity_schwarzschild_radius": ("relativity", "schwarzschild_radius", lambda a: {"mass": a["mass"]}),
    "relativity_lorentz_factor": ("relativity", "lorentz_factor", lambda a: {"velocity": a["velocity"]}),
    "combinatorics_choose": ("combinatorics", "n_choose_r", lambda a: {"n": a["n"], "r": a["r"]}),
}


def execute_tool_call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Executes a tool call the LLM requested, by routing to the REAL
    dispatcher (never re-computed by the LLM itself). `explore_number` is
    handled specially since it isn't a plain dispatcher passthrough."""
    if name == "explore_number":
        from src.math_engine.number_explorer import explore_number
        try:
            result = explore_number(int(arguments["n"]), include_oeis=False)
            return {"status": "ok", "result": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    entry = _TOOL_TO_DISPATCH.get(name)
    if entry is None:
        return {"status": "error", "message": f"Unknown tool '{name}'."}
    category, operation, param_mapper = entry
    try:
        params = param_mapper(arguments)
    except Exception as e:
        return {"status": "error", "message": f"Bad arguments for {name}: {e}"}
    return solve_hard_problem(category, operation, params)
