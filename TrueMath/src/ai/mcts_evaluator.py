"""
Module Name: mcts_evaluator
Purpose: Power the Monte Carlo Tree Search graph to evaluate deep mathematical paths logically.
Responsibilities:
  - Generate UCB1 (Upper Confidence Bound) scores to balance exploration vs exploitation.
  - Maintain a rigid memory-efficient pointer graph of mathematical theorems evaluated.
  - Integrate closely with the state_manager for checkpointing.
Dependencies: math
Input: Branch hashes, AI confidence probabilities.
Output: The `best_child` node pointer to pursue mathematically.
Possible Errors: Deep recursion exhaustions (Stack overflows).
Testing Method: Simulate a multi-branch tree to verify UCB1 weights successfully avoid endless loops.
Estimated Complexity: Very High.
Integration Notes: MCTS instances should be isolated per unresolved mathematical problem.
"""
import math
import weakref
from typing import Dict, List, Optional
from src.core.sys_logger import get_logger

logger = get_logger("MCTSEvaluator")

class MCTSNode:
    """Highly optimized C-style node using slots for memory footprint constraints."""
    __slots__ = ('state_hash', 'visits', 'reward', 'children', 'parent', '__weakref__')
    
    def __init__(self, state_hash: str, parent: Optional['MCTSNode'] = None):
        self.state_hash = state_hash
        self.visits = 0
        self.reward = 0.0
        self.children: List['MCTSNode'] = []
        # Use weakref to surgically prevent deep Python Garbage Collector circular memory leaks
        self.parent = weakref.ref(parent) if parent else None

    def ucb1(self, exploration_weight: float = 1.41) -> float:
        """Calculates standard Upper Confidence Bound for Trees logic."""
        if self.visits == 0:
            return float('inf')
        
        exploitation = self.reward / self.visits
        # Standard UCT formula handles exploration/exploitation tradeoffs
        actual_parent = self.parent() if self.parent else None
        parent_visits = actual_parent.visits if actual_parent and actual_parent.visits > 0 else 1
        exploration = exploration_weight * math.sqrt(math.log(parent_visits) / self.visits)
        return exploitation + exploration

    def ucb1_precalculated(self, exploration_weight: float, parent_log_visits: float) -> float:
        """Calculates UCB1 using pre-calculated log(parent.visits) to eliminate redundent calculations."""
        if self.visits == 0:
            return float('inf')
        
        exploitation = self.reward / self.visits
        exploration = exploration_weight * math.sqrt(parent_log_visits / self.visits)
        return exploitation + exploration

    def ucb1_precalculated_optimized(self, exploration_multiplier: float) -> float:
        """Calculates UCB1 using pre-calculated sibling multiplier to save CPU division and root operations."""
        if self.visits == 0:
            return float('inf')
        
        exploitation = self.reward / self.visits
        exploration = exploration_multiplier / math.sqrt(self.visits)
        return exploitation + exploration

class MCTSTree:
    __slots__ = ('root', 'exploration_weight')
    
    def __init__(self, root_state: str, exploration_weight: float = 1.41):
        # BUG-13 FIX: Accept exploration_weight so config.MCTS_EXPLORATION_WEIGHT is consumed
        self.root = MCTSNode(root_state)
        self.exploration_weight = exploration_weight
        logger.info(f"Initialized new mathematical search branch targeting '{root_state}'")

    def select_best_path(self, current_node: MCTSNode) -> MCTSNode:
        """Traverses the MCTS from start_node selecting the highest scoring UCB1 path."""
        while current_node.children:
            best_node = None
            best_score = -float('inf')
            
            # Precompute log(parent.visits) and exploration scaling once for all sibling children to save CPU cycles
            parent_log_v = math.log(current_node.visits) if current_node.visits > 0 else 0.0
            exploration_multiplier = self.exploration_weight * math.sqrt(parent_log_v)
            
            for child in current_node.children:
                score = child.ucb1_precalculated_optimized(exploration_multiplier)
                if score > best_score:
                    best_score = score
                    best_node = child
                    
            current_node = best_node
        return current_node

    def expand(self, node: MCTSNode, possible_states: List[str]) -> None:
        """Spawns new localized nodes based on AI generated pseudo-ASTs."""
        for state in possible_states:
            child = MCTSNode(state_hash=state, parent=node)
            node.children.append(child)
        logger.debug(f"Expanded node {node.state_hash} into {len(possible_states)} branches.")

    def backpropagate(self, node: MCTSNode, reward: float) -> None:
        """Pushes validation bounds upwards through the tree to adjust UCB weights."""
        current = node
        while current is not None:
            current.visits += 1
            current.reward += reward
            current = current.parent() if current.parent else None
