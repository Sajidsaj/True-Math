from src.math_engine.linear_algebra import determinant, eigenvalues, inverse, matrix_multiply, rank, solve_linear_system


def test_determinant():
    result = determinant([[2, 1], [1, 3]])
    assert result["determinant"] == "5"


def test_determinant_rejects_non_square():
    result = determinant([[1, 2, 3], [4, 5, 6]])
    assert result["status"] == "error"


def test_inverse():
    result = inverse([[2, 1], [1, 3]])
    assert result["status"] == "ok"
    assert result["inverse"] == [["3/5", "-1/5"], ["-1/5", "2/5"]]


def test_inverse_singular_matrix():
    result = inverse([[1, 2], [2, 4]])  # determinant = 0
    assert result["status"] == "error"


def test_eigenvalues():
    result = eigenvalues([[2, 0], [0, 3]])  # diagonal matrix -> eigenvalues are 2, 3
    assert result["status"] == "ok"
    values = {e["value"] for e in result["eigenvalues"]}
    assert values == {"2", "3"}


def test_solve_linear_system():
    # 2x + y = 3, x + 3y = 5  ->  x=4/5, y=7/5
    result = solve_linear_system([[2, 1], [1, 3]], [3, 5])
    assert result["solvable"] is True
    assert result["x"] == ["4/5", "7/5"]


def test_solve_linear_system_underdetermined():
    result = solve_linear_system([[1, 1], [2, 2]], [1, 2])
    assert result["solvable"] is False


def test_matrix_multiply():
    result = matrix_multiply([[1, 2], [3, 4]], [[5, 6], [7, 8]])
    assert result["result"] == [["19", "22"], ["43", "50"]]


def test_rank():
    result = rank([[1, 2, 3], [2, 4, 6]])  # second row is a multiple of the first
    assert result["rank"] == 1


def test_determinant_rejects_oversized_matrix_dos_protection():
    """SECURITY: a 100x100 exact-arithmetic determinant takes 5+ seconds —
    a confirmed CPU-exhaustion DoS vector. Must be rejected instantly."""
    import time
    huge_matrix = [[1] * 100 for _ in range(100)]
    t0 = time.time()
    result = determinant(huge_matrix)
    elapsed = time.time() - t0
    assert result["status"] == "error"
    assert "too large" in result["message"].lower()
    assert elapsed < 1.0  # must reject near-instantly, not attempt the computation


def test_inverse_rejects_oversized_matrix():
    huge_matrix = [[1 if i == j else 0 for j in range(50)] for i in range(50)]
    result = inverse(huge_matrix)
    assert result["status"] == "error"
    assert "too large" in result["message"].lower()
