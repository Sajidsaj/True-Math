"""
Module Name: cognitive_engine
Purpose: Supervise the context window and orchestrate localized LLM inference.
Responsibilities:
  - Provide a safe interface wrapper for the local AI engine (e.g. Llama.cpp).
  - Execute dynamic summarization when the context nears strict hardware exhaustion limits.
  - Implement retry routines and handle model context crash phenomena.
Dependencies: json
Input: Formal math prompts, constraint lists.
Output: LLM generated mathematical pseudo-code / logic.
Possible Errors: Context exhaustion, Out of VRAM faults.
Testing Method: Mocking the LLM generator to test context truncation pathways.
Estimated Complexity: Medium.
Integration Notes: Requires instantiation via `CognitiveCore()`. Calls Graveyard before yielding.
"""
import json
from typing import Dict, List, Optional
from collections import deque
from src.core.sys_logger import get_logger

logger = get_logger("CognitiveEngine")

# BUG-11 FIX: Replace single hardcoded fallback string with a diverse rotation pool.
# When offline (no LLM), the orchestrator cycles through these so the MCTS tree
# never degenerates into an infinite loop on the same expression.
_FALLBACK_HYPOTHESES = (
    "sqrt(x) + sin(y)",
    "exp(-x**2) + cos(y*pi)",
    "log(x + 1) * sin(z)",
    "x**2 + y**2 - z**2",
    "sin(x)**2 + cos(x)**2 - 1",
    "exp(x) - (1 + x + x**2/2)",
)

class ContextExhaustionError(Exception):
    """Raised when a single math step requires more tokens than the hardware limits."""
    pass

class CognitiveCore:
    __slots__ = ('max_tokens', 'current_context', '_approximate_token_count', '_fallback_idx')

    def __init__(self, max_context_tokens: int = 8192):
        self.max_tokens = max_context_tokens
        self.current_context: deque = deque()
        self._approximate_token_count = 0
        self._fallback_idx = 0          # rotation index for offline hypothesis pool
        logger.info(f"Cognitive Engine boundary initialized with {max_context_tokens} tokens.")
        
    def _estimate_tokens(self, text: str) -> int:
        """Heuristic rule of thumb: 1 word ~ 1.3 tokens in complex mathematics typically.
        Uses in-place space counting to avoid list allocations in high-frequency loops."""
        if not text:
            return 0
        return int((text.count(' ') + 1) * 1.3)
        
    def add_to_context(self, role: str, content: str) -> None:
        """Injects new observational arrays into the active window without memory leaks."""
        tk_cost = self._estimate_tokens(content)
        
        if self._approximate_token_count + tk_cost > self.max_tokens:
            logger.warning("Hardware context limit nearing. Engaging automatic structural truncation.")
            self._compress_context()
            
            if self._approximate_token_count + tk_cost > self.max_tokens:
                logger.critical(f"Aborting calculation branch! Prompt size {tk_cost} exceeds structural capabilities.")
                raise ContextExhaustionError("Fatal: Single prompt exceeds hard context limitations.")
                
        self.current_context.append({"role": role, "content": content})
        self._approximate_token_count += tk_cost
        
    def _compress_context(self) -> None:
        """Aggressive tree pruning mechanism discarding non-essential historical context to save VRAM."""
        original_size = self._approximate_token_count
        
        # Target ~80% of max capacity to leave immediate breathing room
        target_size = self.max_tokens * 0.8
        
        # Guard: if context is empty we have nothing to compress
        if not self.current_context:
            return
        
        # Extract system prompt if it exists (it is typically at index 0)
        system_prompt = None
        if self.current_context[0].get("role") == "system":
            system_prompt = self.current_context.popleft()
        
        # Iteratively pop the oldest user/assistant interactions (O(1) speeds)
        # Guard against popping from empty deque after system_prompt removal
        while self._approximate_token_count > target_size and len(self.current_context) > 0:
            dropped_msg = self.current_context.popleft()
            self._approximate_token_count -= self._estimate_tokens(dropped_msg['content'])
            
        # Re-attach system prompt seamlessly to the front if it existed
        if system_prompt:
            self.current_context.appendleft(system_prompt)
            
        logger.info(f"Context efficiently compressed via O(1) deque mutations from {original_size} down to {self._approximate_token_count} active tokens.")

    def reset_context(self) -> None:
        """BUG-07 FIX: Public API to reset context — avoids external callers touching private attrs."""
        self.current_context.clear()
        self._approximate_token_count = 0
        logger.info("Context window reset by orchestrator request.")

    def generate_hypothesis(self) -> str:
        """
        Returns the next hypothesis from the offline rotation pool.
        BUG-11 FIX: was hardcoded to a single string, causing degenerate MCTS loops when LLM is offline.
        """
        logger.debug("Generating offline hypothesis from rotation pool...")
        hypothesis = _FALLBACK_HYPOTHESES[self._fallback_idx % len(_FALLBACK_HYPOTHESES)]
        self._fallback_idx += 1
        self.add_to_context("assistant", hypothesis)
        return hypothesis
