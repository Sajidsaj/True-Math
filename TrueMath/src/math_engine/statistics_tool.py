"""
Module Name: statistics_tool
Purpose: Real descriptive statistics and simple linear regression on
         user-supplied numeric data.
Dependencies: statistics (stdlib)
"""
from __future__ import annotations

import statistics
from typing import Dict, List, Optional


def describe(data: List[float]) -> Dict:
    if not data:
        return {"status": "error", "message": "Data khaali hai."}
    try:
        result = {
            "count": len(data),
            "mean": statistics.mean(data),
            "median": statistics.median(data),
            "mode": statistics.mode(data),
            "min": min(data),
            "max": max(data),
            "range": max(data) - min(data),
            "stdev": statistics.stdev(data) if len(data) > 1 else 0.0,
            "variance": statistics.variance(data) if len(data) > 1 else 0.0,
        }
        return {"status": "ok", **result}
    except statistics.StatisticsError as e:
        return {"status": "error", "message": str(e)}


def linear_regression(x: List[float], y: List[float]) -> Dict:
    """Simple linear regression y = mx + b via least squares (closed-form),
    plus the correlation coefficient r."""
    if len(x) != len(y) or len(x) < 2:
        return {"status": "error", "message": "x aur y same length ke hone chahiye, aur kam se kam 2 points."}

    n = len(x)
    mean_x, mean_y = sum(x) / n, sum(y) / n
    ss_xy = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    ss_xx = sum((xi - mean_x) ** 2 for xi in x)
    ss_yy = sum((yi - mean_y) ** 2 for yi in y)

    if ss_xx == 0:
        return {"status": "error", "message": "All x values are identical — slope is undefined (vertical line)."}

    slope = ss_xy / ss_xx
    intercept = mean_y - slope * mean_x
    r = ss_xy / (ss_xx * ss_yy) ** 0.5 if ss_yy != 0 else 0.0

    return {
        "status": "ok",
        "slope": slope,
        "intercept": intercept,
        "equation": f"y = {slope:.6g}x + {intercept:.6g}",
        "correlation_r": r,
        "r_squared": r ** 2,
    }
