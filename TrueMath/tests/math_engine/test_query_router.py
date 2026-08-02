import os

from src.math_engine.query_router import get_unmatched_queries, route_query


def test_perfect_number_query_routes_correctly():
    result = route_query("is 8128 a perfect number")
    assert result is not None
    assert "perfect number" in result["answer"]
    assert result["verified_ok"] is True


def test_prime_check_query_routes_correctly():
    result = route_query("is 97 prime")
    assert result is not None
    assert "97 is prime" in result["answer"]


def test_factor_query_routes_correctly():
    result = route_query("factor 360")
    assert result is not None
    assert "360" in result["answer"]


def test_gcd_query_routes_correctly():
    result = route_query("gcd of 48 and 18")
    assert result is not None
    assert "6" in result["answer"]


def test_fibonacci_query_routes_correctly():
    result = route_query("fibonacci of 10")
    assert result is not None
    assert "55" in result["answer"]  # F(10) = 55


def test_rsa_keygen_query_routes_correctly():
    result = route_query("generate an RSA key")
    assert result is not None
    assert "BEGIN PUBLIC KEY" in result["answer"]
    assert "BEGIN PRIVATE KEY" in result["answer"]


def test_rsa_keygen_extracts_bit_size():
    result = route_query("create rsa keypair with 3072 bits")
    assert result is not None
    assert "3072-bit" in result["answer"]


def test_mod_pow_query_routes_correctly():
    result = route_query("what is 2^10 mod 1000")
    assert result is not None
    assert "= 24" in result["answer"]  # 1024 mod 1000 = 24


def test_lcm_query_routes_correctly():
    result = route_query("lcm of 4 and 6")
    assert result is not None
    assert "12" in result["answer"]


def test_mod_inverse_query_routes_correctly():
    result = route_query("modular inverse of 3 mod 11")
    assert result is not None
    assert "4" in result["answer"]


def test_choose_query_routes_correctly():
    result = route_query("10 choose 3")
    assert result is not None
    assert "120" in result["answer"]


def test_permute_query_routes_correctly():
    result = route_query("permutations of 10 and 3")
    assert result is not None
    assert "720" in result["answer"]


def test_catalan_query_routes_correctly():
    result = route_query("catalan number of 5")
    assert result is not None
    assert "42" in result["answer"]


def test_physics_constant_query_routes_correctly():
    result = route_query("speed of light")
    assert result is not None
    assert "299792458" in result["answer"]


def test_schwarzschild_query_handles_scientific_notation():
    result = route_query("schwarzschild radius of 1.989e30 kg")
    assert result is not None
    assert "2954" in result["answer"]


def test_lorentz_factor_query_not_confused_with_factorization():
    # Regression test: "lorentz factor" contains the substring "factor" and
    # must NOT be caught by the generic factorization pattern.
    result = route_query("lorentz factor at 0.8c")
    assert result is not None
    assert "1.6666" in result["answer"] or "1.667" in result["answer"]


def test_unit_convert_query_routes_correctly():
    result = route_query("convert 100 km to miles")
    assert result is not None
    assert "62.13" in result["answer"] or "62.1" in result["answer"]


def test_temperature_convert_query_routes_correctly():
    result = route_query("100 celsius to fahrenheit")
    assert result is not None
    assert "212" in result["answer"]


def test_kinetic_energy_query_routes_correctly():
    result = route_query("kinetic energy of mass 2 and velocity 10")
    assert result is not None
    assert "100" in result["answer"]


def test_factor_still_works_after_reordering():
    # Regression test: the generic factorization pattern must still work
    # for genuine factorization requests after the reordering fix.
    result = route_query("factor 123456789")
    assert result is not None
    assert "3" in result["answer"]


def test_unmatched_query_returns_none_and_gets_logged(tmp_path, monkeypatch):
    import src.math_engine.query_router as qr
    log_path = str(tmp_path / "unmatched.log")
    monkeypatch.setattr(qr, "_UNMATCHED_LOG_PATH", log_path)

    result = route_query("what is the deep philosophical meaning of zero")
    assert result is None
    assert os.path.exists(log_path)
    with open(log_path, encoding="utf-8") as f:
        content = f.read()
    assert "philosophical meaning of zero" in content


def test_get_unmatched_queries_returns_list(tmp_path, monkeypatch):
    import src.math_engine.query_router as qr
    log_path = str(tmp_path / "unmatched2.log")
    monkeypatch.setattr(qr, "_UNMATCHED_LOG_PATH", log_path)

    route_query("some totally unmatched question one")
    route_query("some totally unmatched question two")
    queries = get_unmatched_queries()
    assert len(queries) == 2
