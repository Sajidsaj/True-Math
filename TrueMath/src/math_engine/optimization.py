"""
Module Name: optimization
Purpose: Real optimization algorithms for coding use — linear programming,
         shortest path, and 0/1 knapsack. Genuine solvers (scipy's HiGHS
         LP solver, Dijkstra's algorithm, dynamic programming), not
         LLM-guessed heuristics.
Responsibilities:
  - linear_program: general LP solver (minimize c^T x subject to linear
    constraints) via scipy.optimize.linprog (HiGHS backend).
  - shortest_path: Dijkstra's algorithm over a weighted graph.
  - knapsack_01: classic 0/1 knapsack via dynamic programming (exact,
    exponential-worst-case problem solved in pseudo-polynomial time).
Dependencies: scipy, heapq
Honesty note: Linear programming and shortest-path are solved exactly and
              optimally — these are genuinely "solved" problems with known
              polynomial algorithms. 0/1 knapsack is NP-hard in general but
              this DP solves it exactly for reasonable weight/capacity
              sizes (pseudo-polynomial in the capacity, not the problem
              size) — it will get slow/memory-heavy for very large
              capacities, which is expected, not a bug.
Security note: knapsack_01 enforces hard input-size caps (see
              _MAX_KNAPSACK_CAPACITY / _MAX_KNAPSACK_ITEMS below) —
              confirmed during a security review that an uncapped capacity
              (e.g. 50,000,000) causes the O(items * capacity) DP table to
              exhaust CPU/memory within seconds, a real DoS vector on a
              publicly reachable deployment.
"""
from __future__ import annotations

import heapq
from typing import Dict, List, Optional, Tuple, TypedDict

from scipy.optimize import linprog


class LPResult(TypedDict, total=False):
    status: str
    success: bool
    x: list
    objective_value: float
    message: str


def linear_program(
    c: List[float],
    A_ub: Optional[List[List[float]]] = None,
    b_ub: Optional[List[float]] = None,
    A_eq: Optional[List[List[float]]] = None,
    b_eq: Optional[List[float]] = None,
    bounds: Optional[List[Tuple[Optional[float], Optional[float]]]] = None,
) -> LPResult:
    """Minimizes c^T x subject to A_ub @ x <= b_ub and/or A_eq @ x == b_eq
    (standard scipy.optimize.linprog convention). To MAXIMIZE an objective,
    pass the negated coefficients for c.

    Example — maximize 3x + 5y subject to x <= 4, 2y <= 12, 3x + 2y <= 18:
        linear_program(c=[-3, -5], A_ub=[[1,0],[0,2],[3,2]], b_ub=[4,12,18])
    """
    result = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
    return {
        "status": "ok" if result.success else "infeasible_or_error",
        "success": bool(result.success),
        "x": [round(float(v), 6) for v in result.x] if result.success else [],
        "objective_value": round(float(result.fun), 6) if result.success else None,
        "message": result.message,
    }


def shortest_path(graph: Dict[str, Dict[str, float]], start: str, end: str) -> dict:
    """Dijkstra's algorithm over a weighted directed graph given as an
    adjacency dict: {"A": {"B": 4, "C": 1}, "B": {...}, ...}.
    Returns the shortest distance and the actual path, or reports
    unreachable if no path exists."""
    if start not in graph:
        return {"status": "error", "message": f"Start node '{start}' not in graph."}

    distances = {node: float("inf") for node in graph}
    distances[start] = 0
    previous = {}
    visited = set()
    pq = [(0, start)]

    while pq:
        dist, node = heapq.heappop(pq)
        if node in visited:
            continue
        visited.add(node)
        if node == end:
            break
        for neighbor, weight in graph.get(node, {}).items():
            new_dist = dist + weight
            if new_dist < distances.get(neighbor, float("inf")):
                distances[neighbor] = new_dist
                previous[neighbor] = node
                heapq.heappush(pq, (new_dist, neighbor))

    if end not in distances or distances[end] == float("inf"):
        return {"status": "ok", "reachable": False, "message": f"No path found from {start} to {end}."}

    path = [end]
    while path[-1] != start:
        path.append(previous[path[-1]])
    path.reverse()

    return {"status": "ok", "reachable": True, "distance": distances[end], "path": path}


def knapsack_01(weights: List[int], values: List[float], capacity: int) -> dict:
    """Exact 0/1 knapsack via dynamic programming: choose a subset of items
    (each used at most once) maximizing total value without exceeding
    `capacity` total weight. Returns the optimal value and which items are
    chosen (by index).

    SECURITY: capacity and item count are hard-capped (see module
    docstring) — the DP table is O(items * capacity) in both time and
    memory, so an uncapped request is a real resource-exhaustion DoS
    vector on a publicly reachable server."""
    _MAX_KNAPSACK_CAPACITY = 100_000
    _MAX_KNAPSACK_ITEMS = 1_000

    if len(weights) > _MAX_KNAPSACK_ITEMS:
        return {"status": "error", "message": f"Too many items (max {_MAX_KNAPSACK_ITEMS})."}
    if capacity > _MAX_KNAPSACK_CAPACITY or capacity < 0:
        return {"status": "error", "message": f"Capacity out of range (0 to {_MAX_KNAPSACK_CAPACITY})."}

    n = len(weights)
    dp = [[0.0] * (capacity + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        w, v = weights[i - 1], values[i - 1]
        for cap in range(capacity + 1):
            dp[i][cap] = dp[i - 1][cap]
            if w <= cap:
                dp[i][cap] = max(dp[i][cap], dp[i - 1][cap - w] + v)

    # Backtrack to find which items were chosen
    chosen = []
    cap = capacity
    for i in range(n, 0, -1):
        if dp[i][cap] != dp[i - 1][cap]:
            chosen.append(i - 1)
            cap -= weights[i - 1]
    chosen.reverse()

    return {
        "status": "ok",
        "optimal_value": dp[n][capacity],
        "chosen_item_indices": chosen,
        "total_weight_used": sum(weights[i] for i in chosen),
    }
