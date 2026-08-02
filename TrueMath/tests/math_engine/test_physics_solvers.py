import pytest

from src.math_engine.physics_solvers import kinetic_energy, momentum, newtons_second_law, solve_kinematics


def test_kinematics_free_fall():
    # Free fall from rest, a=9.8, t=2 -> v=19.6, s=19.6
    result = solve_kinematics(u=0, a=9.8, t=2)
    assert result["status"] == "ok"
    assert result["solved"]["v"] == pytest.approx(19.6)
    assert result["solved"]["s"] == pytest.approx(19.6)
    assert result["still_unknown"] == []


def test_kinematics_solves_acceleration_and_time_from_uvs():
    # u=0, v=20, s=100 -> a=2, t=10 (v^2 = u^2 + 2as)
    result = solve_kinematics(u=0, v=20, s=100)
    assert result["solved"]["a"] == pytest.approx(2.0)
    assert result["solved"]["t"] == pytest.approx(10.0)


def test_kinematics_insufficient_data():
    result = solve_kinematics(u=0)
    assert result["status"] == "error"


def test_kinetic_energy():
    result = kinetic_energy(mass=2, velocity=10)
    assert result["kinetic_energy_joules"] == 100.0


def test_momentum():
    result = momentum(mass=2, velocity=10)
    assert result["momentum_kg_m_s"] == 20


def test_newtons_second_law_solve_force():
    result = newtons_second_law(mass=5, acceleration=2)
    assert result["force_newtons"] == 10


def test_newtons_second_law_solve_mass():
    result = newtons_second_law(force=10, acceleration=2)
    assert result["mass_kg"] == 5
