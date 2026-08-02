from src.math_engine.discovery_engine import discover_identity


def test_discover_identity_is_always_verified():
    # Every generated identity instance must be symbolically verified true
    # (that's the whole point of the module) — check across many samples
    # since the template/substitution is randomized.
    for _ in range(30):
        result = discover_identity()
        assert result["verified_equal"] is True
        assert result["base_identity"]
        assert result["lhs"]
        assert result["rhs"]
