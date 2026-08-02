"""
Module Name: algebra_sandbox
Purpose: Lets a user define a completely CUSTOM finite mathematical
         universe — their own set of elements and their own operation
         rule(s) (a Cayley/operation table) — and mechanically, exactly
         verifies what kind of algebraic structure it forms (magma,
         semigroup, monoid, group, abelian group, and — with a second
         operation — ring/field).
Responsibilities:
  - Validate a user-supplied operation table is well-formed (closed: every
    result is one of the declared elements).
  - Check associativity, commutativity, identity element, inverses —
    exhaustively, by brute-force checking every combination (feasible for
    small finite sets, which is the whole point of a "sandbox").
  - Classify the structure based on which properties hold.
  - With two operations (add + multiply), also check distributivity and
    classify ring/field-like structures.
Dependencies: none (pure Python, brute-force verification over the
              user-supplied finite set)
Honesty note: This is a genuine, mechanically-verified classification of
              whatever custom rules you invent — you truly can define a
              brand new set of elements and a brand new operation nobody
              has written down before, and this will correctly tell you
              its real algebraic properties. That said, "new" here means
              "a structure you made up and nobody catalogued" — the
              CONCEPTS being checked (associativity, groups, rings) are
              well-established 19th/20th-century abstract algebra, not
              new mathematics. Every finite structure you can build this
              way is almost certainly isomorphic to something already
              classified (finite groups up to fairly large orders are
              fully catalogued) — but the exploration and verification
              are 100% real and yours.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple, TypedDict


class StructureReport(TypedDict, total=False):
    status: str
    message: str
    elements: list
    closed: bool
    associative: bool
    commutative: bool
    identity: object
    has_inverses: bool
    inverses: dict
    classification: str
    failing_example: str


def _validate_table(elements: List, table: Dict[str, Dict[str, object]]) -> Optional[str]:
    """Returns an error message if the table is malformed/not closed, else None."""
    element_set = set(elements)
    for a in elements:
        row = table.get(str(a)) or table.get(a)
        if row is None:
            return f"Table is missing a row for element {a!r}."
        for b in elements:
            key = str(b) if str(b) in row else b
            if key not in row:
                return f"Table row for {a!r} is missing an entry for {b!r}."
            result = row[key]
            if result not in element_set:
                return f"Table entry ({a!r}, {b!r}) = {result!r} is not in the declared element set — not closed."
    return None


def _op(table: Dict, a, b):
    row = table.get(str(a), table.get(a))
    return row.get(str(b), row.get(b))


def check_associativity(elements: List, table: Dict) -> Tuple[bool, Optional[str]]:
    for a in elements:
        for b in elements:
            for c in elements:
                lhs = _op(table, _op(table, a, b), c)
                rhs = _op(table, a, _op(table, b, c))
                if lhs != rhs:
                    return False, f"({a}∘{b})∘{c} = {lhs}, but {a}∘({b}∘{c}) = {rhs}"
    return True, None


def check_commutativity(elements: List, table: Dict) -> Tuple[bool, Optional[str]]:
    for a in elements:
        for b in elements:
            if _op(table, a, b) != _op(table, b, a):
                return False, f"{a}∘{b} = {_op(table, a, b)}, but {b}∘{a} = {_op(table, b, a)}"
    return True, None


def find_identity(elements: List, table: Dict):
    for e in elements:
        if all(_op(table, e, a) == a and _op(table, a, e) == a for a in elements):
            return e
    return None


def find_inverses(elements: List, table: Dict, identity) -> Optional[Dict]:
    if identity is None:
        return None
    inverses = {}
    for a in elements:
        inv = next((b for b in elements if _op(table, a, b) == identity and _op(table, b, a) == identity), None)
        if inv is None:
            return None  # not every element has an inverse
        inverses[a] = inv
    return inverses


def classify_structure(elements: List, table: Dict) -> StructureReport:
    """Runs the full mechanical classification of a user-defined finite
    algebraic structure (elements + one binary operation table)."""
    error = _validate_table(elements, table)
    if error:
        return {"status": "error", "message": error}

    assoc, assoc_fail = check_associativity(elements, table)
    comm, comm_fail = check_commutativity(elements, table)
    identity = find_identity(elements, table)
    inverses = find_inverses(elements, table, identity) if identity is not None else None

    if assoc and identity is not None and inverses is not None:
        classification = "Abelian Group" if comm else "Group (non-abelian)"
    elif assoc and identity is not None:
        classification = "Monoid (has identity, but not every element has an inverse)"
    elif assoc:
        classification = "Semigroup (associative, but no identity element)"
    else:
        classification = "Magma (closed, but not associative — the weakest structure checked here)"

    return {
        "status": "ok",
        "elements": elements,
        "closed": True,
        "associative": assoc,
        "associativity_counterexample": assoc_fail,
        "commutative": comm,
        "commutativity_counterexample": comm_fail,
        "identity": identity,
        "has_inverses": inverses is not None,
        "inverses": inverses,
        "classification": classification,
    }


def classify_ring(elements: List, add_table: Dict, mul_table: Dict) -> StructureReport:
    """Classifies a user-defined structure with TWO operations (addition and
    multiplication) as a ring / commutative ring / field, checking
    distributivity in addition to each operation's own properties."""
    add_report = classify_structure(elements, add_table)
    if add_report["status"] != "ok":
        return {"status": "error", "message": f"Addition table invalid: {add_report['message']}"}

    mul_error = _validate_table(elements, mul_table)
    if mul_error:
        return {"status": "error", "message": f"Multiplication table invalid: {mul_error}"}

    mul_assoc, mul_assoc_fail = check_associativity(elements, mul_table)
    mul_comm, _ = check_commutativity(elements, mul_table)
    mul_identity = find_identity(elements, mul_table)

    # Distributivity: a*(b+c) = a*b + a*c for all a,b,c
    distributive = True
    dist_fail = None
    for a in elements:
        for b in elements:
            for c in elements:
                lhs = _op(mul_table, a, _op(add_table, b, c))
                rhs = _op(add_table, _op(mul_table, a, b), _op(mul_table, a, c))
                if lhs != rhs:
                    distributive = False
                    dist_fail = f"{a}*({b}+{c}) = {lhs}, but ({a}*{b})+({a}*{c}) = {rhs}"
                    break
            if not distributive:
                break
        if not distributive:
            break

    is_abelian_group_under_add = add_report["classification"] == "Abelian Group"

    if is_abelian_group_under_add and mul_assoc and distributive:
        if mul_identity is not None:
            zero = add_report["identity"]
            nonzero = [e for e in elements if e != zero]
            mul_inverses_exist = all(
                any(_op(mul_table, a, b) == mul_identity for b in nonzero) for a in nonzero
            ) if nonzero else True
            if mul_comm and mul_inverses_exist:
                classification = "Field (every non-zero element has a multiplicative inverse)"
            elif mul_comm:
                classification = "Commutative Ring with Identity (not every element invertible)"
            else:
                classification = "Ring with Identity (multiplication not commutative)"
        else:
            classification = "Ring (no multiplicative identity)"
    else:
        classification = "Not a ring — fails one of: abelian group under +, associative *, or distributivity"

    return {
        "status": "ok",
        "elements": elements,
        "additive_structure": add_report["classification"],
        "multiplicative_associative": mul_assoc,
        "multiplicative_commutative": mul_comm,
        "multiplicative_identity": mul_identity,
        "distributive": distributive,
        "distributivity_counterexample": dist_fail,
        "classification": classification,
    }
