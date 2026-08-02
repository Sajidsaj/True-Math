import pytest

from src.math_engine.relativity import (
    C,
    gravitational_time_dilation,
    length_contraction,
    lorentz_factor,
    relativistic_energy,
    relativistic_velocity_addition,
    schwarzschild_radius,
    time_dilation,
)


def test_lorentz_factor_at_0_8c():
    result = lorentz_factor(0.8 * C)
    assert result["gamma"] == pytest.approx(5 / 3, abs=1e-9)


def test_lorentz_factor_rejects_faster_than_light():
    result = lorentz_factor(C * 1.01)
    assert result["status"] == "error"


def test_time_dilation():
    result = time_dilation(proper_time=1.0, velocity=0.8 * C)
    assert result["dilated_time"] == pytest.approx(5 / 3, abs=1e-9)


def test_length_contraction():
    result = length_contraction(proper_length=10.0, velocity=0.8 * C)
    assert result["contracted_length"] == pytest.approx(6.0, abs=1e-9)


def test_rest_mass_energy_e_equals_mc_squared():
    result = relativistic_energy(mass=1.0)
    # The famous number: 1 kg of rest mass = ~8.988e16 Joules
    assert result["rest_energy_joules"] == pytest.approx(8.9875e16, rel=1e-4)
    assert result["kinetic_energy_joules"] == pytest.approx(0.0, abs=1.0)


def test_velocity_addition_never_exceeds_c():
    result = relativistic_velocity_addition(0.9 * C, 0.9 * C)
    assert result["combined_velocity"] < C


def test_schwarzschild_radius_of_the_sun():
    # Known real value: ~2953-2954 meters for the Sun's mass
    result = schwarzschild_radius(1.989e30)
    assert result["schwarzschild_radius_meters"] == pytest.approx(2954, abs=5)


def test_schwarzschild_radius_of_earth():
    # Known real value: ~8.87 mm
    result = schwarzschild_radius(5.972e24)
    assert result["schwarzschild_radius_meters"] * 1000 == pytest.approx(8.87, abs=0.01)


def test_gps_gravitational_time_dilation_matches_published_figure():
    # The well-known GPS relativistic correction: satellite clocks gain
    # about 45.7 microseconds/day from gravitational time dilation alone
    # (before the smaller special-relativistic velocity correction).
    m_earth = 5.972e24
    r_gps = 26560000
    r_surface = 6371000
    gps = gravitational_time_dilation(m_earth, r_gps)
    surface = gravitational_time_dilation(m_earth, r_surface)
    diff_microseconds_per_day = abs(gps["time_dilation_factor"] / surface["time_dilation_factor"] - 1) * 86400 * 1e6
    assert diff_microseconds_per_day == pytest.approx(45.7, abs=0.5)
