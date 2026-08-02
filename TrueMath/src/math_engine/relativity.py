"""
Module Name: relativity
Purpose: Real Special and General Relativity calculations using the
         standard, well-established formulas from those theories.
Responsibilities (Special Relativity):
  - Lorentz factor (gamma)
  - Time dilation, length contraction
  - Relativistic momentum and total energy (E = gamma*m*c^2)
  - Relativistic velocity addition
Responsibilities (General Relativity):
  - Schwarzschild radius (event horizon of a non-rotating black hole)
  - Gravitational time dilation (clocks run slower in stronger gravity —
    the real effect GPS satellites must correct for)
  - Gravitational redshift
Dependencies: math
Honesty note: These are the STANDARD, well-established formulas from
              special and general relativity (textbook physics, not novel
              research) — genuinely correct and useful for real problems
              (GPS time correction, black hole event horizons, particle
              accelerator energies). This is NOT full numerical GR (solving
              Einstein's field equations for arbitrary spacetimes,
              gravitational wave simulation, etc.) — those require tensor
              calculus and specialized numerical-relativity software, a
              fundamentally different scale of tool. What's here are the
              closed-form results GR gives for simple, high-symmetry cases
              (a non-rotating spherical mass), which is what these
              formulas are actually valid for.
"""
from __future__ import annotations

import math
from typing import Dict

C = 299792458.0          # speed of light, m/s (exact, SI-defined)
G = 6.67430e-11          # gravitational constant, m^3 kg^-1 s^-2


def lorentz_factor(velocity: float) -> Dict:
    """gamma = 1 / sqrt(1 - v^2/c^2). Requires |v| < c."""
    if abs(velocity) >= C:
        return {"status": "error", "message": "Velocity must be less than the speed of light (c)."}
    gamma = 1.0 / math.sqrt(1 - (velocity / C) ** 2)
    return {"status": "ok", "gamma": gamma, "velocity": velocity}


def time_dilation(proper_time: float, velocity: float) -> Dict:
    """delta_t_observed = gamma * delta_t_proper — a moving clock (as seen
    by a stationary observer) ticks slower by a factor of gamma."""
    g = lorentz_factor(velocity)
    if g["status"] != "ok":
        return g
    return {"status": "ok", "dilated_time": g["gamma"] * proper_time, "gamma": g["gamma"]}


def length_contraction(proper_length: float, velocity: float) -> Dict:
    """L_observed = L_proper / gamma — a moving object appears shorter
    (along its direction of motion) to a stationary observer."""
    g = lorentz_factor(velocity)
    if g["status"] != "ok":
        return g
    return {"status": "ok", "contracted_length": proper_length / g["gamma"], "gamma": g["gamma"]}


def relativistic_momentum(mass: float, velocity: float) -> Dict:
    """p = gamma * m * v (reduces to classical p=mv when v << c)."""
    g = lorentz_factor(velocity)
    if g["status"] != "ok":
        return g
    return {"status": "ok", "momentum_kg_m_s": g["gamma"] * mass * velocity, "gamma": g["gamma"]}


def relativistic_energy(mass: float, velocity: float = 0.0) -> Dict:
    """Total energy E = gamma*m*c^2. At v=0, this is the famous rest-mass
    energy E = mc^2. Also reports kinetic energy = total - rest energy."""
    g = lorentz_factor(velocity)
    if g["status"] != "ok":
        return g
    rest_energy = mass * C ** 2
    total_energy = g["gamma"] * rest_energy
    return {
        "status": "ok",
        "rest_energy_joules": rest_energy,
        "total_energy_joules": total_energy,
        "kinetic_energy_joules": total_energy - rest_energy,
        "gamma": g["gamma"],
    }


def relativistic_velocity_addition(v1: float, v2: float) -> Dict:
    """Combines two velocities relativistically:
    u = (v1+v2)/(1 + v1*v2/c^2) — classical addition (u=v1+v2) is only an
    approximation that breaks down as velocities approach c; this never
    exceeds c."""
    if abs(v1) >= C or abs(v2) >= C:
        return {"status": "error", "message": "Both velocities must be less than c."}
    result = (v1 + v2) / (1 + (v1 * v2) / C ** 2)
    return {"status": "ok", "combined_velocity": result}


def schwarzschild_radius(mass: float) -> Dict:
    """r_s = 2GM/c^2 — the radius at which a non-rotating mass would become
    a black hole (its escape velocity would equal c). Exact for the
    idealized (non-rotating, uncharged) case."""
    r_s = 2 * G * mass / C ** 2
    return {"status": "ok", "schwarzschild_radius_meters": r_s, "mass_kg": mass}


def gravitational_time_dilation(mass: float, radius: float) -> Dict:
    """Clocks at radius r from a mass M tick slower by a factor of
    1/sqrt(1 - 2GM/(rc^2)) compared to a clock infinitely far away. This is
    the real effect GPS satellites correct for (their clocks run FASTER
    than ground clocks since they're farther from Earth's mass, by about
    45 microseconds/day — partly offset by SR time dilation from their
    orbital velocity, netting about +38 microseconds/day, which GPS
    corrects for)."""
    schwarzschild_term = 2 * G * mass / (radius * C ** 2)
    if schwarzschild_term >= 1:
        return {"status": "error", "message": "Radius is at or inside the Schwarzschild radius — formula breaks down (this would be inside/at the event horizon)."}
    factor = 1.0 / math.sqrt(1 - schwarzschild_term)
    return {"status": "ok", "time_dilation_factor": factor, "mass_kg": mass, "radius_m": radius}


def gravitational_redshift(mass: float, emitted_radius: float, observed_radius: float) -> Dict:
    """Ratio of observed to emitted wavelength for light climbing out of a
    gravity well from emitted_radius to observed_radius (observed_radius
    should be >= emitted_radius, e.g. light escaping to a distant
    observer)."""
    term_emit = 1 - 2 * G * mass / (emitted_radius * C ** 2)
    term_obs = 1 - 2 * G * mass / (observed_radius * C ** 2)
    if term_emit <= 0 or term_obs <= 0:
        return {"status": "error", "message": "One of the radii is at/inside the Schwarzschild radius — formula breaks down."}
    ratio = math.sqrt(term_emit / term_obs)
    return {"status": "ok", "wavelength_ratio_observed_over_emitted": 1 / ratio, "redshift_z": (1 / ratio) - 1}
