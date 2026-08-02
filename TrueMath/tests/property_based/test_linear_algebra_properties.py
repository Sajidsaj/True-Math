"""Property-based tests for linear_algebra.py — checks fundamental linear
algebra identities hold across many randomly generated matrices."""
import sympy
from hypothesis import given, settings
from hypothesis import strategies as st

from src.math_engine.linear_algebra import determinant, inverse, matrix_multiply

_SMALL_MATRIX_ENTRY = st.integers(min_value=-5, max_value=5)


def _random_2x2():
    return st.lists(st.lists(_SMALL_MATRIX_ENTRY, min_size=2, max_size=2), min_size=2, max_size=2)


@given(_random_2x2(), _random_2x2())
@settings(max_examples=200)
def test_determinant_of_product_equals_product_of_determinants(A, B):
    det_a = sympy.sympify(determinant(A)["determinant"])
    det_b = sympy.sympify(determinant(B)["determinant"])
    product_result = matrix_multiply(A, B)
    det_ab = sympy.sympify(determinant([[sympy.sympify(v) for v in row] for row in product_result["result"]])["determinant"])
    assert det_ab == det_a * det_b


@given(_random_2x2())
@settings(max_examples=200)
def test_matrix_times_its_inverse_is_identity(A):
    det_result = determinant(A)
    if sympy.sympify(det_result["determinant"]) == 0:
        return  # singular matrix has no inverse, skip
    inv_result = inverse(A)
    assert inv_result["status"] == "ok"
    inv_matrix = [[sympy.sympify(v) for v in row] for row in inv_result["inverse"]]
    product = matrix_multiply(A, inv_matrix)
    product_matrix = [[sympy.sympify(v) for v in row] for row in product["result"]]
    # A * A^-1 must be the identity matrix
    n = len(A)
    for i in range(n):
        for j in range(n):
            expected = 1 if i == j else 0
            assert product_matrix[i][j] == expected
