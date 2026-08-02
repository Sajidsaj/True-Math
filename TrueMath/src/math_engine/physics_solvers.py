"""
Module Name: physics_solvers
Purpose: Solves the standard kinematics (SUVAT) equations, plus common
         energy/momentum formulas — given whichever variables you know,
         it figures out which equation applies and solves for the rest.
Dependencies: none
Honesty note: These are the standard high-school/intro-college physics
              equations (constant acceleration only) — not general
              relativity, not variable acceleration. Standard, correct,
              and useful for exactly the class of problems they're built
              for.
"""
from __future__ import annotations

from typing import Dict, Optional


def solve_kinematics(u: Optional[float] = None, v: Optional[float] = None,
                      a: Optional[float] = None, t: Optional[float] = None,
                      s: Optional[float] = None) -> Dict:
    """SUVAT equations for constant acceleration: given any 3 of
    {u (initial velocity), v (final velocity), a (acceleration), t (time),
    s (displacement)}, solves for the other 2 where possible.

    v = u + at
    s = ut + 0.5at^2
    v^2 = u^2 + 2as
    s = ((u+v)/2)*t
    """
    known = {"u": u, "v": v, "a": a, "t": t, "s": s}
    known_count = sum(1 for val in known.values() if val is not None)
    if known_count < 2:
        return {"status": "error", "message": "Kam se kam 2 known variables do (u, v, a, t, s mein se) taake baaki solve ho sakein."}

    result = dict(known)
    changed = True
    while changed:
        changed = False
        if result["v"] is None and result["u"] is not None and result["a"] is not None and result["t"] is not None:
            result["v"] = result["u"] + result["a"] * result["t"]
            changed = True
        if result["u"] is None and result["v"] is not None and result["a"] is not None and result["t"] is not None:
            result["u"] = result["v"] - result["a"] * result["t"]
            changed = True
        if result["a"] is None and result["v"] is not None and result["u"] is not None and result["t"] not in (None, 0):
            result["a"] = (result["v"] - result["u"]) / result["t"]
            changed = True
        if result["t"] is None and result["v"] is not None and result["u"] is not None and result["a"] not in (None, 0):
            result["t"] = (result["v"] - result["u"]) / result["a"]
            changed = True
        if result["s"] is None and result["u"] is not None and result["t"] is not None and result["a"] is not None:
            result["s"] = result["u"] * result["t"] + 0.5 * result["a"] * result["t"] ** 2
            changed = True
        if result["s"] is None and result["u"] is not None and result["v"] is not None and result["t"] is not None:
            result["s"] = 0.5 * (result["u"] + result["v"]) * result["t"]
            changed = True
        if result["v"] is None and result["u"] is not None and result["a"] is not None and result["s"] is not None:
            v_squared = result["u"] ** 2 + 2 * result["a"] * result["s"]
            if v_squared >= 0:
                result["v"] = v_squared ** 0.5
                changed = True
        if result["a"] is None and result["v"] is not None and result["u"] is not None and result["s"] not in (None, 0):
            result["a"] = (result["v"] ** 2 - result["u"] ** 2) / (2 * result["s"])
            changed = True

    solved = {k: v_ for k, v_ in result.items() if v_ is not None}
    unsolved = [k for k, v_ in result.items() if v_ is None]
    return {"status": "ok", "solved": solved, "still_unknown": unsolved}


def kinetic_energy(mass: float, velocity: float) -> Dict:
    return {"status": "ok", "kinetic_energy_joules": 0.5 * mass * velocity ** 2}


def potential_energy(mass: float, height: float, g: float = 9.80665) -> Dict:
    return {"status": "ok", "potential_energy_joules": mass * g * height}


def momentum(mass: float, velocity: float) -> Dict:
    return {"status": "ok", "momentum_kg_m_s": mass * velocity}


def newtons_second_law(mass: Optional[float] = None, force: Optional[float] = None,
                        acceleration: Optional[float] = None) -> Dict:
    """F = ma — solves for whichever one is missing."""
    known = [x for x in (mass, force, acceleration) if x is not None]
    if len(known) < 2:
        return {"status": "error", "message": "Kam se kam 2 diye jaane chahiye (mass, force, acceleration mein se)."}
    if force is None:
        return {"status": "ok", "force_newtons": mass * acceleration}
    if mass is None:
        return {"status": "ok", "mass_kg": force / acceleration}
    if acceleration is None:
        return {"status": "ok", "acceleration_m_s2": force / mass}
    return {"status": "ok", "message": "All three given — no unknown to solve for.", "check": mass * acceleration == force}
