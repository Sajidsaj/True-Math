import pytest
from src.memory.graveyard_rag import GraveyardDB

def test_bury_and_query_exact_match(tmp_path):
    """Ensure exact vectors achieve high 99%+ cosine similarity."""
    db_path = tmp_path / "test_exact.db"
    db = GraveyardDB(str(db_path))
    
    vec1 = [1.0, 0.0, 0.5, 0.1]
    db.bury_path("hash_exact", "Timeout in Lean 4", vec1)
    
    results = db.query_graveyard(vec1, threshold=0.99)
    assert len(results) == 1
    assert results[0]['ast_hash'] == "hash_exact"
    assert results[0]['reason'] == "Timeout in Lean 4"
    assert results[0]['similarity'] > 0.99

def test_bury_and_query_approximate_match(tmp_path):
    """Evaluate resilience on thresholding for near-identical failed approaches."""
    db_path = tmp_path / "test_approx.db"
    db = GraveyardDB(str(db_path))
    
    vec1 = [0.8, 0.2, 0.1, 0.5]
    vec_sim = [0.85, 0.15, 0.1, 0.45] # Very similar
    vec_diff = [-0.8, 0.9, -0.1, 0.0] # completely different dimension trajectory
    
    db.bury_path("hash_base", "Logical Circular Paradox", vec1)
    
    # Should find the similar vector at a modest threshold
    res_sim = db.query_graveyard(vec_sim, threshold=0.90)
    assert len(res_sim) == 1
    
    # Should absolutely filter out orthogonal/opposite vectors
    res_diff = db.query_graveyard(vec_diff, threshold=0.50)
    assert len(res_diff) == 0

def test_handling_invalid_dimensions(tmp_path):
    """Ensure robust degradation when dimensionality spaces mismatch."""
    db_path = tmp_path / "test_dim.db"
    db = GraveyardDB(str(db_path))
    
    db.bury_path("hash_3", "Error", [1, 2, 3])
    
    # Query with 2 dimensions instead of 3
    res_invalid_dim = db.query_graveyard([1, 2], threshold=0.1)
    assert len(res_invalid_dim) == 0
