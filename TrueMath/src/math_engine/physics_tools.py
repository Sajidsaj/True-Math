"""
Module Name: physics_tools
Purpose: Real physics constants (2018 CODATA recommended values) and vector
         operations (dot/cross product, magnitude, normalization, angle
         between vectors) — genuine, standard physics building blocks.
Dependencies: math
"""
from __future__ import annotations

import math
from typing import Dict, List

# 2018 CODATA recommended values (exact where defined by SI redefinition)
CONSTANTS: Dict[str, Dict] = {
    "speed_of_light": {"value": 299792458, "unit": "m/s", "symbol": "c"},
    "gravitational_constant": {"value": 6.67430e-11, "unit": "m^3 kg^-1 s^-2", "symbol": "G"},
    "planck_constant": {"value": 6.62607015e-34, "unit": "J*s", "symbol": "h"},
    "reduced_planck_constant": {"value": 1.054571817e-34, "unit": "J*s", "symbol": "ħ"},
    "elementary_charge": {"value": 1.602176634e-19, "unit": "C", "symbol": "e"},
    "electron_mass": {"value": 9.1093837015e-31, "unit": "kg", "symbol": "m_e"},
    "proton_mass": {"value": 1.67262192369e-27, "unit": "kg", "symbol": "m_p"},
    "avogadro_number": {"value": 6.02214076e23, "unit": "mol^-1", "symbol": "N_A"},
    "boltzmann_constant": {"value": 1.380649e-23, "unit": "J/K", "symbol": "k_B"},
    "gas_constant": {"value": 8.314462618, "unit": "J mol^-1 K^-1", "symbol": "R"},
    "vacuum_permittivity": {"value": 8.8541878128e-12, "unit": "F/m", "symbol": "ε₀"},
    "vacuum_permeability": {"value": 1.25663706212e-6, "unit": "N/A^2", "symbol": "μ₀"},
    "standard_gravity": {"value": 9.80665, "unit": "m/s^2", "symbol": "g"},
    "stefan_boltzmann_constant": {"value": 5.670374419e-8, "unit": "W m^-2 K^-4", "symbol": "σ"},
}


def get_constant(name: str) -> dict:
    key = name.strip().lower().replace(" ", "_")
    if key not in CONSTANTS:
        return {"status": "error", "message": f"Unknown constant '{name}'. Available: {list(CONSTANTS.keys())}"}
    return {"status": "ok", "name": key, **CONSTANTS[key]}


def list_constants() -> dict:
    return {"status": "ok", "constants": CONSTANTS}


def _validate_vector(v) -> bool:
    return isinstance(v, list) and len(v) >= 1 and all(isinstance(c, (int, float)) for c in v)


def dot_product(a: List[float], b: List[float]) -> dict:
    if not (_validate_vector(a) and _validate_vector(b)) or len(a) != len(b):
        return {"status": "error", "message": "Vectors must be numeric lists of the same length."}
    return {"status": "ok", "result": sum(x * y for x, y in zip(a, b))}


def cross_product(a: List[float], b: List[float]) -> dict:
    if len(a) != 3 or len(b) != 3:
        return {"status": "error", "message": "Cross product is only defined for 3D vectors."}
    result = [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]
    return {"status": "ok", "result": result}


def magnitude(v: List[float]) -> dict:
    if not _validate_vector(v):
        return {"status": "error", "message": "Vector must be a numeric list."}
    return {"status": "ok", "result": math.sqrt(sum(c ** 2 for c in v))}


def normalize(v: List[float]) -> dict:
    mag_result = magnitude(v)
    if mag_result["status"] != "ok":
        return mag_result
    mag = mag_result["result"]
    if mag == 0:
        return {"status": "error", "message": "Cannot normalize the zero vector."}
    return {"status": "ok", "result": [c / mag for c in v]}


def angle_between(a: List[float], b: List[float]) -> dict:
    dot_result = dot_product(a, b)
    if dot_result["status"] != "ok":
        return dot_result
    mag_a, mag_b = magnitude(a)["result"], magnitude(b)["result"]
    if mag_a == 0 or mag_b == 0:
        return {"status": "error", "message": "Cannot compute angle involving the zero vector."}
    cos_theta = max(-1.0, min(1.0, dot_result["result"] / (mag_a * mag_b)))
    radians = math.acos(cos_theta)
    return {"status": "ok", "radians": radians, "degrees": math.degrees(radians)}
