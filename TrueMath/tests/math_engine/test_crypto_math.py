from src.math_engine.crypto_math import discrete_log_bsgs, factor_integer, rsa_decrypt, rsa_encrypt, rsa_toy_keygen


def test_factor_integer():
    result = factor_integer(9797)
    assert result["prime_factors"] == [97, 101]
    assert result["is_prime"] is False

    result_prime = factor_integer(97)
    assert result_prime["is_prime"] is True


def test_discrete_log_bsgs():
    # 5^6 mod 23 = 8
    result = discrete_log_bsgs(g=5, h=8, p=23)
    assert result["status"] == "ok"
    assert result["x"] == 6
    assert pow(5, result["x"], 23) == 8


def test_rsa_toy_roundtrip():
    keys = rsa_toy_keygen(bits=16)
    assert keys["status"] == "ok"
    message = 42
    ciphertext = rsa_encrypt(message, keys["public_key"]["e"], keys["public_key"]["n"])
    plaintext = rsa_decrypt(ciphertext, keys["private_key"]["d"], keys["private_key"]["n"])
    assert plaintext == message
