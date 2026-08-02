import pytest

from src.math_engine.physics_tools import (
    angle_between,
    cross_product,
    dot_product,
    get_constant,
    list_constants,
    magnitude,
    normalize,
)


def test_get_constant():
    result = get_constant("speed_of_light")
    assert result["status"] == "ok"
    assert result["value"] == 299792458


def test_get_constant_unknown():
    result = get_constant("made_up_constant")
    assert result["status"] == "error"


def test_list_constants():
    result = list_constants()
    assert result["status"] == "ok"
    assert "speed_of_light" in result["constants"]


def test_dot_product():
    result = dot_product([1, 2, 3], [4, 5, 6])
    assert result["result"] == 32


def test_cross_product_unit_vectors():
    # x-hat cross y-hat = z-hat
    result = cross_product([1, 0, 0], [0, 1, 0])
    assert result["result"] == [0, 0, 1]


def test_cross_product_requires_3d():
    result = cross_product([1, 2], [3, 4])
    assert result["status"] == "error"


def test_magnitude_3_4_5_triangle():
    result = magnitude([3, 4])
    assert result["result"] == 5.0


def test_normalize():
    result = normalize([3, 4])
    assert result["result"] == pytest.approx([0.6, 0.8])


def test_normalize_zero_vector_rejected():
    result = normalize([0, 0])
    assert result["status"] == "error"


def test_angle_between_perpendicular_vectors():
    result = angle_between([1, 0], [0, 1])
    assert result["degrees"] == pytest.approx(90.0)
