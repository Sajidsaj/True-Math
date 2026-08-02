"""Property-based tests for unit_converter.py — converting A->B->A must
always return (approximately) the original value, for any pair of units in
the same dimension."""
from hypothesis import given, settings
from hypothesis import strategies as st

from src.math_engine.unit_converter import _UNITS, convert

_UNIT_NAMES = list(_UNITS.keys())


@given(
    st.sampled_from(_UNIT_NAMES),
    st.sampled_from(_UNIT_NAMES),
    st.floats(min_value=0.001, max_value=1_000_000, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=500)
def test_roundtrip_conversion_returns_original_value(unit_a, unit_b, value):
    dim_a, _ = _UNITS[unit_a]
    dim_b, _ = _UNITS[unit_b]
    if dim_a != dim_b:
        return  # only meaningful within the same physical dimension

    forward = convert(value, unit_a, unit_b)
    assert forward["status"] == "ok"
    backward = convert(forward["value"], unit_b, unit_a)
    assert backward["status"] == "ok"
    assert backward["value"] == pytest_approx(value)


def pytest_approx(value, rel=1e-6):
    import pytest
    return pytest.approx(value, rel=rel)


@given(
    st.sampled_from(_UNIT_NAMES),
    st.sampled_from(_UNIT_NAMES),
    st.floats(min_value=1, max_value=1000, allow_nan=False),
)
@settings(max_examples=300)
def test_convert_never_crashes_on_valid_units(unit_a, unit_b, value):
    # Should always return a clean status dict, never raise an exception —
    # even for cross-dimension conversions (which should error gracefully).
    result = convert(value, unit_a, unit_b)
    assert result["status"] in ("ok", "error")
