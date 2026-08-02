"""
Module Name: falsification_engine
Purpose: Pre-filter AI proposals via ultra-fast brute-force statistical counter-examples before hitting Lean 4.
Responsibilities:
  - Generate massive random numerical bounds (floats, ints, negatives, zero, infinites).
  - Substitute bounds into AI generated math equations natively.
  - Return immediate failure if a counter-example is found, saving intensive formal validation OS calls.
Dependencies: random, math, ast
Input: Python AST formatted mathematical theorem strings.
Output: Boolean (True if it survives brute force, False if statistically disproven).
Possible Errors: Floating point precision drift, ZeroDivision.
Testing Method: Pass universally false math (x + 1 = x * 2) and expect immediate rejection.
Estimated Complexity: Very High.
Integration Notes: Protects Lean4 Bridge from bottlenecking on blatantly stupid AI propositions.
"""
import random
import math
from typing import Callable, Dict, Any, List, Tuple
from src.core.sys_logger import get_logger

logger = get_logger("FalsificationEngine")

class FalsificationEngine:
    __slots__ = ('iterations', 'range_bounds', '_pre_cached_matrix')
    
    def __init__(self, iterations: int = 1000):
        # We test thousands of numbers per mathematical theory in O(1) loop time
        self.iterations = iterations
        # Complex bounding guarantees we hit standard edge cases natively
        self.range_bounds = [-1e6, -1.0, -0.0001, 0.0, 0.0001, 1.0, 1e6, math.pi, math.e]
        self._pre_cached_matrix = self._generate_base_matrix(max_vars=10)
        logger.info(f"Falsification Statistical Engine spun up with {self.iterations} brute-force limits. Matrix pre-cached!")

    def _generate_base_matrix(self, max_vars: int) -> Tuple[Tuple[float, ...], ...]:
        """Pre-caches a massive immutable tensor-like array in memory. 
        Bypasses native CPU Random-Number-Generator bottlenecking completely."""
        cases = []
        for _ in range(self.iterations):
            # Inline generator instantly destructures values instead of dynamically mapping array lengths
            case = tuple(
                random.choice(self.range_bounds) if random.random() < 0.2 else random.uniform(-1000.0, 1000.0)
                for _ in range(max_vars)
            )
            cases.append(case)
        return tuple(cases)

    def structural_brute_force(self, lambda_equation: Callable, vars_expected: int) -> bool:
        """
        Takes a highly restricted mathematical lambda and literally throws massive noise at it.
        If the lambda returns False even ONCE, the mathematical equation is formally disproven instantly.
        """
        # BUG-10 FIX: The previous code used a generator expression:
        #   test_matrix = (row[:vars_expected] for row in self._pre_cached_matrix)
        # Generator objects are exhausted after ONE iteration. From epoch 2 onwards,
        # structural_brute_force evaluated ZERO test cases and returned True for everything.
        # Fix: iterate the tuple directly each call — it is never consumed.
        for row in self._pre_cached_matrix:
            case = row[:vars_expected]
            try:
                result = lambda_equation(*case)
                if result is False:
                    return False
            except (ZeroDivisionError, OverflowError, ValueError, TypeError, RecursionError):
                return False
                
        # The equation SURVIVED all statistical brute force! It is highly likely to be true.
        # Now it is worthy of formal (slow) Lean 4 OS verification.
        logger.debug("Theorem survived brute-force statistical matrix. Ready for formal Lean 4 Kernel.")
        return True
