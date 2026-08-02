"""
Module Name: unit_converter
Purpose: Real unit conversion with dimensional analysis — converts between
         units of the same physical dimension (length, mass, time, etc.)
         and refuses (with a clear error) to convert between incompatible
         dimensions (e.g. meters to kilograms), catching a very common
         source of physics/engineering bugs.
Dependencies: none
"""
from __future__ import annotations

from typing import Dict

# Each unit maps to (dimension_name, factor_to_base_SI_unit).
# Base units: length=meter, mass=kilogram, time=second, temperature=kelvin,
# energy=joule, force=newton, pressure=pascal, speed=m/s, area=m^2, volume=m^3.
_UNITS: Dict[str, tuple] = {
    # length (base: meter)
    "m": ("length", 1.0), "meter": ("length", 1.0), "meters": ("length", 1.0),
    "km": ("length", 1000.0), "kilometer": ("length", 1000.0),
    "cm": ("length", 0.01), "mm": ("length", 0.001),
    "mile": ("length", 1609.344), "miles": ("length", 1609.344),
    "yard": ("length", 0.9144), "foot": ("length", 0.3048), "ft": ("length", 0.3048),
    "inch": ("length", 0.0254), "in": ("length", 0.0254),
    "nautical_mile": ("length", 1852.0), "light_year": ("length", 9.4607e15),

    # mass (base: kilogram)
    "kg": ("mass", 1.0), "kilogram": ("mass", 1.0),
    "g": ("mass", 0.001), "gram": ("mass", 0.001), "mg": ("mass", 1e-6),
    "lb": ("mass", 0.45359237), "pound": ("mass", 0.45359237), "lbs": ("mass", 0.45359237),
    "oz": ("mass", 0.0283495), "ounce": ("mass", 0.0283495),
    "tonne": ("mass", 1000.0), "ton": ("mass", 1000.0),

    # time (base: second)
    "s": ("time", 1.0), "sec": ("time", 1.0), "second": ("time", 1.0), "seconds": ("time", 1.0),
    "min": ("time", 60.0), "minute": ("time", 60.0), "minutes": ("time", 60.0),
    "hr": ("time", 3600.0), "hour": ("time", 3600.0), "hours": ("time", 3600.0),
    "day": ("time", 86400.0), "days": ("time", 86400.0),
    "year": ("time", 31557600.0), "years": ("time", 31557600.0),

    # speed (base: m/s)
    "m/s": ("speed", 1.0), "km/h": ("speed", 0.277778), "kmh": ("speed", 0.277778),
    "mph": ("speed", 0.44704), "knot": ("speed", 0.514444), "ft/s": ("speed", 0.3048),

    # energy (base: joule)
    "j": ("energy", 1.0), "joule": ("energy", 1.0), "joules": ("energy", 1.0),
    "kj": ("energy", 1000.0), "cal": ("energy", 4.184), "calorie": ("energy", 4.184),
    "kcal": ("energy", 4184.0), "wh": ("energy", 3600.0), "kwh": ("energy", 3.6e6),
    "ev": ("energy", 1.602176634e-19),

    # force (base: newton)
    "n": ("force", 1.0), "newton": ("force", 1.0), "lbf": ("force", 4.44822), "dyne": ("force", 1e-5),

    # pressure (base: pascal)
    "pa": ("pressure", 1.0), "pascal": ("pressure", 1.0), "kpa": ("pressure", 1000.0),
    "bar": ("pressure", 1e5), "atm": ("pressure", 101325.0), "psi": ("pressure", 6894.76),

    # area (base: m^2)
    "m^2": ("area", 1.0), "km^2": ("area", 1e6), "hectare": ("area", 1e4), "acre": ("area", 4046.86),

    # volume (base: m^3)
    "m^3": ("volume", 1.0), "liter": ("volume", 0.001), "l": ("volume", 0.001),
    "ml": ("volume", 1e-6), "gallon": ("volume", 0.00378541),
}


def convert(value: float, from_unit: str, to_unit: str) -> dict:
    """Converts `value` from `from_unit` to `to_unit`, refusing (with a
    clear message) if the two units aren't the same physical dimension —
    genuine dimensional analysis, not just a lookup table."""
    fu, tu = from_unit.strip().lower(), to_unit.strip().lower()

    if fu not in _UNITS:
        return {"status": "error", "message": f"Unknown unit '{from_unit}'. See list_units for supported units."}
    if tu not in _UNITS:
        return {"status": "error", "message": f"Unknown unit '{to_unit}'. See list_units for supported units."}

    dim_from, factor_from = _UNITS[fu]
    dim_to, factor_to = _UNITS[tu]

    if dim_from != dim_to:
        return {
            "status": "error",
            "message": f"Dimension mismatch: '{from_unit}' is a {dim_from} unit, '{to_unit}' is a {dim_to} unit — cannot convert.",
        }

    base_value = value * factor_from
    result = base_value / factor_to
    return {"status": "ok", "value": result, "from_unit": from_unit, "to_unit": to_unit, "dimension": dim_from}


def convert_temperature(value: float, from_unit: str, to_unit: str) -> dict:
    """Temperature needs special handling (affine, not linear, conversion —
    can't just multiply by a factor like other units)."""
    fu, tu = from_unit.strip().lower(), to_unit.strip().lower()
    valid = {"c", "celsius", "f", "fahrenheit", "k", "kelvin"}
    if fu not in valid or tu not in valid:
        return {"status": "error", "message": "Temperature units must be c/celsius, f/fahrenheit, or k/kelvin."}

    # Convert to Celsius first
    if fu.startswith("f"):
        celsius = (value - 32) * 5 / 9
    elif fu.startswith("k"):
        celsius = value - 273.15
    else:
        celsius = value

    if tu.startswith("f"):
        result = celsius * 9 / 5 + 32
    elif tu.startswith("k"):
        result = celsius + 273.15
    else:
        result = celsius

    return {"status": "ok", "value": result, "from_unit": from_unit, "to_unit": to_unit, "dimension": "temperature"}


def list_units() -> dict:
    dims: Dict[str, list] = {}
    for unit, (dim, _) in _UNITS.items():
        dims.setdefault(dim, []).append(unit)
    dims["temperature"] = ["c/celsius", "f/fahrenheit", "k/kelvin"]
    return {"status": "ok", "units_by_dimension": dims}
