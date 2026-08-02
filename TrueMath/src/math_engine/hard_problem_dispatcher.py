"""
Module Name: hard_problem_dispatcher
Purpose: Single entry point that routes a (category, operation, params)
         request to the right real solver function — number theory,
         optimization, crypto-math, or combinatorics. Used by both the
         TrueMath dashboard (via IPC) and directly as a Python library.
Usage as a library:
    from src.math_engine.hard_problem_dispatcher import solve
    solve("number_theory", "gcd", {"a": 48, "b": 18})
    # -> {"status": "ok", "result": 6}
"""
from __future__ import annotations

from typing import Any, Dict

from src.math_engine import combinatorics, crypto_math, number_theory, optimization, real_crypto, algebra_sandbox
from src.math_engine import linear_algebra, differential_equations, statistics_tool
from src.math_engine import unit_converter, physics_tools, physics_solvers, complexity_analyzer, relativity
from src.math_engine import number_explorer

_OPERATIONS = {
    ("number_theory", "gcd"): lambda p: number_theory.gcd(p["a"], p["b"]),
    ("number_theory", "lcm"): lambda p: number_theory.lcm(p["a"], p["b"]),
    ("number_theory", "extended_gcd"): lambda p: number_theory.extended_gcd(p["a"], p["b"]),
    ("number_theory", "mod_inverse"): lambda p: number_theory.mod_inverse(p["a"], p["m"]),
    ("number_theory", "mod_pow"): lambda p: number_theory.mod_pow(p["base"], p["exp"], p["mod"]),
    ("number_theory", "is_prime"): lambda p: number_theory.is_prime(p["n"]),
    ("number_theory", "prime_factors"): lambda p: number_theory.prime_factors(p["n"]),
    ("number_theory", "crt"): lambda p: number_theory.chinese_remainder(p["remainders"], p["moduli"]),
    ("number_theory", "diophantine"): lambda p: number_theory.solve_linear_diophantine(p["a"], p["b"], p["c"]),

    ("optimization", "linear_program"): lambda p: optimization.linear_program(
        p["c"], p.get("A_ub"), p.get("b_ub"), p.get("A_eq"), p.get("b_eq"), p.get("bounds")
    ),
    ("optimization", "shortest_path"): lambda p: optimization.shortest_path(p["graph"], p["start"], p["end"]),
    ("optimization", "knapsack"): lambda p: optimization.knapsack_01(p["weights"], p["values"], p["capacity"]),

    ("crypto", "factor"): lambda p: crypto_math.factor_integer(p["n"]),
    ("crypto", "discrete_log"): lambda p: crypto_math.discrete_log_bsgs(p["g"], p["h"], p["p"]),
    ("crypto", "rsa_keygen"): lambda p: crypto_math.rsa_toy_keygen(p.get("bits", 16)),
    ("crypto", "rsa_encrypt"): lambda p: crypto_math.rsa_encrypt(p["message"], p["e"], p["n"]),
    ("crypto", "rsa_decrypt"): lambda p: crypto_math.rsa_decrypt(p["cipher"], p["d"], p["n"]),

    ("combinatorics", "n_choose_r"): lambda p: combinatorics.n_choose_r(p["n"], p["r"]),
    ("combinatorics", "n_permute_r"): lambda p: combinatorics.n_permute_r(p["n"], p["r"]),
    ("combinatorics", "fibonacci"): lambda p: combinatorics.fibonacci(p["n"]),
    ("combinatorics", "catalan"): lambda p: combinatorics.catalan_number(p["n"]),
    ("combinatorics", "summary"): lambda p: combinatorics.combinatorics_summary(p["n"], p.get("r", 0)),

    ("real_crypto", "generate_keypair"): lambda p: real_crypto.generate_rsa_keypair(p.get("key_size", 2048)),
    ("real_crypto", "encrypt"): lambda p: real_crypto.rsa_encrypt_real(p["message"], p["public_key_pem"]),
    ("real_crypto", "decrypt"): lambda p: real_crypto.rsa_decrypt_real(p["ciphertext"], p["private_key_pem"]),
    ("real_crypto", "sign"): lambda p: real_crypto.rsa_sign_real(p["message"], p["private_key_pem"]),
    ("real_crypto", "verify"): lambda p: real_crypto.rsa_verify_real(p["message"], p["signature"], p["public_key_pem"]),

    ("algebra_sandbox", "classify_structure"): lambda p: algebra_sandbox.classify_structure(p["elements"], p["table"]),
    ("algebra_sandbox", "classify_ring"): lambda p: algebra_sandbox.classify_ring(p["elements"], p["add_table"], p["mul_table"]),

    ("linear_algebra", "determinant"): lambda p: linear_algebra.determinant(p["matrix"]),
    ("linear_algebra", "inverse"): lambda p: linear_algebra.inverse(p["matrix"]),
    ("linear_algebra", "eigenvalues"): lambda p: linear_algebra.eigenvalues(p["matrix"]),
    ("linear_algebra", "solve_system"): lambda p: linear_algebra.solve_linear_system(p["A"], p["b"]),
    ("linear_algebra", "multiply"): lambda p: linear_algebra.matrix_multiply(p["A"], p["B"]),
    ("linear_algebra", "rank"): lambda p: linear_algebra.rank(p["matrix"]),

    ("differential_equations", "solve_ode"): lambda p: differential_equations.solve_ode(p["equation"], p.get("ics")),

    ("statistics", "describe"): lambda p: statistics_tool.describe(p["data"]),
    ("statistics", "linear_regression"): lambda p: statistics_tool.linear_regression(p["x"], p["y"]),

    ("unit_converter", "convert"): lambda p: unit_converter.convert(p["value"], p["from_unit"], p["to_unit"]),
    ("unit_converter", "convert_temperature"): lambda p: unit_converter.convert_temperature(p["value"], p["from_unit"], p["to_unit"]),
    ("unit_converter", "list_units"): lambda p: unit_converter.list_units(),

    ("physics", "get_constant"): lambda p: physics_tools.get_constant(p["name"]),
    ("physics", "list_constants"): lambda p: physics_tools.list_constants(),
    ("physics", "dot_product"): lambda p: physics_tools.dot_product(p["a"], p["b"]),
    ("physics", "cross_product"): lambda p: physics_tools.cross_product(p["a"], p["b"]),
    ("physics", "magnitude"): lambda p: physics_tools.magnitude(p["v"]),
    ("physics", "normalize"): lambda p: physics_tools.normalize(p["v"]),
    ("physics", "angle_between"): lambda p: physics_tools.angle_between(p["a"], p["b"]),
    ("physics", "kinematics"): lambda p: physics_solvers.solve_kinematics(
        p.get("u"), p.get("v"), p.get("a"), p.get("t"), p.get("s")
    ),
    ("physics", "kinetic_energy"): lambda p: physics_solvers.kinetic_energy(p["mass"], p["velocity"]),
    ("physics", "potential_energy"): lambda p: physics_solvers.potential_energy(p["mass"], p["height"], p.get("g", 9.80665)),
    ("physics", "momentum"): lambda p: physics_solvers.momentum(p["mass"], p["velocity"]),
    ("physics", "newtons_second_law"): lambda p: physics_solvers.newtons_second_law(
        p.get("mass"), p.get("force"), p.get("acceleration")
    ),

    ("coding_tools", "analyze_complexity"): lambda p: complexity_analyzer.analyze_complexity(p["code"]),

    ("relativity", "lorentz_factor"): lambda p: relativity.lorentz_factor(p["velocity"]),
    ("relativity", "time_dilation"): lambda p: relativity.time_dilation(p["proper_time"], p["velocity"]),
    ("relativity", "length_contraction"): lambda p: relativity.length_contraction(p["proper_length"], p["velocity"]),
    ("relativity", "relativistic_momentum"): lambda p: relativity.relativistic_momentum(p["mass"], p["velocity"]),
    ("relativity", "relativistic_energy"): lambda p: relativity.relativistic_energy(p["mass"], p.get("velocity", 0.0)),
    ("relativity", "velocity_addition"): lambda p: relativity.relativistic_velocity_addition(p["v1"], p["v2"]),
    ("relativity", "schwarzschild_radius"): lambda p: relativity.schwarzschild_radius(p["mass"]),
    ("relativity", "gravitational_time_dilation"): lambda p: relativity.gravitational_time_dilation(p["mass"], p["radius"]),
    ("relativity", "gravitational_redshift"): lambda p: relativity.gravitational_redshift(
        p["mass"], p["emitted_radius"], p["observed_radius"]
    ),

    ("number_explorer", "explore"): lambda p: number_explorer.explore_number(p["n"], p.get("include_oeis", True)),
}

CATEGORIES = {
    "number_theory": ["gcd", "lcm", "extended_gcd", "mod_inverse", "mod_pow", "is_prime", "prime_factors", "crt", "diophantine"],
    "optimization": ["linear_program", "shortest_path", "knapsack"],
    "crypto": ["factor", "discrete_log", "rsa_keygen", "rsa_encrypt", "rsa_decrypt"],
    "combinatorics": ["n_choose_r", "n_permute_r", "fibonacci", "catalan", "summary"],
    "real_crypto": ["generate_keypair", "encrypt", "decrypt", "sign", "verify"],
    "algebra_sandbox": ["classify_structure", "classify_ring"],
    "linear_algebra": ["determinant", "inverse", "eigenvalues", "solve_system", "multiply", "rank"],
    "differential_equations": ["solve_ode"],
    "statistics": ["describe", "linear_regression"],
    "unit_converter": ["convert", "convert_temperature", "list_units"],
    "physics": ["get_constant", "list_constants", "dot_product", "cross_product", "magnitude", "normalize",
                "angle_between", "kinematics", "kinetic_energy", "potential_energy", "momentum", "newtons_second_law"],
    "coding_tools": ["analyze_complexity"],
    "relativity": ["lorentz_factor", "time_dilation", "length_contraction", "relativistic_momentum",
                   "relativistic_energy", "velocity_addition", "schwarzschild_radius",
                   "gravitational_time_dilation", "gravitational_redshift"],
    "number_explorer": ["explore"],
}


def solve(category: str, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Routes to the right solver. Always returns a dict with 'status'
    ('ok' or 'error') so callers never need a try/except for normal
    (expected) failure modes like missing params or infeasible problems."""
    fn = _OPERATIONS.get((category, operation))
    if fn is None:
        return {
            "status": "error",
            "message": f"Unknown operation '{category}.{operation}'. "
                       f"Valid operations for '{category}': {CATEGORIES.get(category, 'unknown category')}",
        }
    try:
        result = fn(params or {})
        return {"status": "ok", "result": result}
    except KeyError as e:
        return {"status": "error", "message": f"Missing required parameter: {e}"}
    except Exception as e:
        return {"status": "error", "message": f"{type(e).__name__}: {e}"}
