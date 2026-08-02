import pytest

from src.math_engine.unit_converter import convert, convert_temperature, list_units


def test_convert_speed():
    result = convert(100, "km/h", "m/s")
    assert result["status"] == "ok"
    assert result["value"] == pytest.approx(27.7778, abs=0.001)


def test_convert_length():
    result = convert(1, "mile", "km")
    assert result["status"] == "ok"
    assert result["value"] == pytest.approx(1.609344)


def test_convert_mass():
    result = convert(5, "kg", "lb")
    assert result["status"] == "ok"
    assert result["value"] == pytest.approx(11.0231, abs=0.001)


def test_convert_dimension_mismatch_rejected():
    result = convert(1, "m", "kg")
    assert result["status"] == "error"
    assert "mismatch" in result["message"].lower()


def test_convert_unknown_unit():
    result = convert(1, "smoots", "m")
    assert result["status"] == "error"


def test_temperature_conversion():
    result = convert_temperature(100, "celsius", "fahrenheit")
    assert result["value"] == pytest.approx(212.0)

    result2 = convert_temperature(0, "celsius", "kelvin")
    assert result2["value"] == pytest.approx(273.15)


def test_list_units_returns_dimensions():
    result = list_units()
    assert result["status"] == "ok"
    assert "length" in result["units_by_dimension"]
    assert "mass" in result["units_by_dimension"]
