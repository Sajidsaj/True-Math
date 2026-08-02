from src.math_engine.complexity_analyzer import analyze_complexity


def _first(code):
    result = analyze_complexity(code)
    assert result["status"] == "ok"
    return result["functions"][0]


def test_no_loops_is_constant():
    entry = _first("def f(x):\n    return x + 1\n")
    assert "O(1)" in entry["estimated_complexity"]


def test_single_loop_is_linear():
    entry = _first("def f(arr):\n    for x in arr:\n        print(x)\n")
    assert entry["estimated_complexity"].startswith("O(n)")


def test_nested_loops_is_quadratic():
    code = (
        "def bubble_sort(arr):\n"
        "    for i in range(len(arr)):\n"
        "        for j in range(len(arr)-1):\n"
        "            pass\n"
    )
    entry = _first(code)
    assert "O(n^2)" in entry["estimated_complexity"]


def test_logarithmic_while_loop():
    code = (
        "def count_bits(n):\n"
        "    count = 0\n"
        "    while n > 0:\n"
        "        n = n // 2\n"
        "        count += 1\n"
        "    return count\n"
    )
    entry = _first(code)
    assert "O(log n)" in entry["estimated_complexity"]
    assert entry["has_logarithmic_loop"] is True


def test_binary_search_is_logarithmic():
    code = (
        "def bs(arr, target, n):\n"
        "    if n <= 0:\n"
        "        return False\n"
        "    return bs(arr, target, n // 2)\n"
    )
    entry = _first(code)
    assert entry["is_recursive"] is True
    assert "O(log n)" in entry["estimated_complexity"]


def test_merge_sort_is_n_log_n():
    code = (
        "def merge_sort(arr, n):\n"
        "    if n <= 1:\n"
        "        return arr\n"
        "    merge_sort(arr, n // 2)\n"
        "    merge_sort(arr, n // 2)\n"
        "    for i in range(n):\n"
        "        pass\n"
        "    return arr\n"
    )
    entry = _first(code)
    assert "log n" in entry["estimated_complexity"]
    assert "n^1" in entry["estimated_complexity"]


def test_fibonacci_is_exponential():
    code = "def fib(n):\n    if n <= 1:\n        return n\n    return fib(n-1) + fib(n-2)\n"
    entry = _first(code)
    assert "2^n" in entry["estimated_complexity"]


def test_factorial_is_linear_recursion():
    code = "def fact(n):\n    if n <= 1:\n        return 1\n    return n * fact(n-1)\n"
    entry = _first(code)
    assert entry["estimated_complexity"].startswith("O(n)")


def test_invalid_syntax_reports_error():
    result = analyze_complexity("def f(:\n  broken")
    assert result["status"] == "error"


def test_no_function_reports_error():
    result = analyze_complexity("x = 1 + 1")
    assert result["status"] == "error"
