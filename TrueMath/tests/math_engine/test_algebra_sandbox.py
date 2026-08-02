from src.math_engine.algebra_sandbox import classify_ring, classify_structure


def _mod_table(n, op):
    elements = list(range(n))
    return {a: {b: op(a, b) % n for b in elements} for a in elements}


def test_z4_addition_is_abelian_group():
    elements = [0, 1, 2, 3]
    table = _mod_table(4, lambda a, b: a + b)
    result = classify_structure(elements, table)
    assert result["status"] == "ok"
    assert result["classification"] == "Abelian Group"
    assert result["identity"] == 0
    assert result["inverses"] == {0: 0, 1: 3, 2: 2, 3: 1}


def test_z5_star_multiplication_is_abelian_group():
    elements = [1, 2, 3, 4]
    table = {a: {b: (a * b) % 5 for b in elements} for a in elements}
    result = classify_structure(elements, table)
    assert result["classification"] == "Abelian Group"
    assert result["identity"] == 1


def test_non_associative_custom_rule_is_magma():
    # a op b = (a - b) mod 3 is closed but NOT associative
    elements = [0, 1, 2]
    table = {a: {b: (a - b) % 3 for b in elements} for a in elements}
    result = classify_structure(elements, table)
    assert result["associative"] is False
    assert "Magma" in result["classification"]


def test_z4_ring_is_commutative_ring_not_field():
    elements = [0, 1, 2, 3]
    add_table = _mod_table(4, lambda a, b: a + b)
    mul_table = _mod_table(4, lambda a, b: a * b)
    result = classify_ring(elements, add_table, mul_table)
    assert "Field" not in result["classification"]
    assert "Commutative Ring" in result["classification"]


def test_z5_ring_is_a_field():
    elements = [0, 1, 2, 3, 4]
    add_table = _mod_table(5, lambda a, b: a + b)
    mul_table = _mod_table(5, lambda a, b: a * b)
    result = classify_ring(elements, add_table, mul_table)
    assert "Field" in result["classification"]


def test_non_closed_table_is_rejected():
    elements = [0, 1]
    bad_table = {0: {0: 0, 1: 5}, 1: {0: 1, 1: 0}}  # 5 is not in elements
    result = classify_structure(elements, bad_table)
    assert result["status"] == "error"
