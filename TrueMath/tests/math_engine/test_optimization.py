from src.math_engine.optimization import knapsack_01, linear_program, shortest_path


def test_linear_program_maximize():
    # Classic textbook LP: maximize 3x+5y s.t. x<=4, 2y<=12, 3x+2y<=18
    result = linear_program(c=[-3, -5], A_ub=[[1, 0], [0, 2], [3, 2]], b_ub=[4, 12, 18])
    assert result["success"] is True
    assert result["x"] == [2.0, 6.0]
    assert result["objective_value"] == -36.0


def test_linear_program_infeasible():
    # x >= 5 and x <= 1 simultaneously — no solution exists
    result = linear_program(c=[1], A_ub=[[1], [-1]], b_ub=[1, -5])
    assert result["success"] is False


def test_shortest_path():
    graph = {"A": {"B": 4, "C": 1}, "C": {"B": 1, "D": 5}, "B": {"D": 1}, "D": {}}
    result = shortest_path(graph, "A", "D")
    assert result["reachable"] is True
    assert result["distance"] == 3
    assert result["path"] == ["A", "C", "B", "D"]


def test_shortest_path_unreachable():
    graph = {"A": {"B": 1}, "B": {}, "C": {}}
    result = shortest_path(graph, "A", "C")
    assert result["reachable"] is False


def test_knapsack():
    result = knapsack_01(weights=[2, 3, 4, 5], values=[3, 4, 5, 6], capacity=5)
    assert result["optimal_value"] == 7.0
    assert result["total_weight_used"] <= 5
    assert set(result["chosen_item_indices"]) == {0, 1}


def test_knapsack_rejects_oversized_capacity_dos_protection():
    """SECURITY: an uncapped capacity causes an O(items * capacity) DP
    table allocation — confirmed a real multi-second CPU/memory-exhaustion
    DoS with capacity=50,000,000. Must be rejected instantly."""
    import time
    t0 = time.time()
    result = knapsack_01(weights=[1], values=[1], capacity=50_000_000)
    elapsed = time.time() - t0
    assert result["status"] == "error"
    assert elapsed < 1.0


def test_knapsack_rejects_too_many_items():
    result = knapsack_01(weights=[1] * 2000, values=[1] * 2000, capacity=100)
    assert result["status"] == "error"
