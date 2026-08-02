import pytest
import math
from src.ai.mcts_evaluator import MCTSNode, MCTSTree

def test_ucb1_prioritizes_unvisited():
    """Verify that novel math pathways are given priority initially."""
    parent = MCTSNode("root")
    parent.visits = 10
    
    child = MCTSNode("child_branch_a", parent=parent)
    # Visits == 0 should yield float('inf')
    assert child.ucb1() == float('inf')

def test_ucb1_exploitation_vs_exploration():
    """Verify calculation bounds for weighted math equations."""
    parent = MCTSNode("root")
    parent.visits = 100
    
    child_high_reward = MCTSNode("child_a", parent=parent)
    child_high_reward.visits = 10
    child_high_reward.reward = 9.0  # High success rate (0.9)
    
    child_low_reward = MCTSNode("child_b", parent=parent)
    child_low_reward.visits = 10
    child_low_reward.reward = 2.0  # Low success rate (0.2)
    
    assert child_high_reward.ucb1() > child_low_reward.ucb1()

def test_mcts_tree_lifecycle():
    """Verify a complete cycle of Expansion, Selection, and Backpropagation."""
    tree = MCTSTree("riemann_base_00")
    
    # Expand AI bounds
    tree.expand(tree.root, ["path_1", "path_2"])
    assert len(tree.root.children) == 2
    
    # Backpropagate a successful Lean 4 proof check on path 1!
    tree.backpropagate(tree.root.children[0], reward=1.0)
    
    # Root should see the update
    assert tree.root.visits == 1
    assert tree.root.reward == 1.0
    
    # Selection should favor the unvisited path_2 (infinite priority) 
    # instead of exploiting path_1
    best = tree.select_best_path(tree.root)
    assert best.state_hash == "path_2"
