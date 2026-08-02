from src.math_engine.real_crypto import (
    generate_rsa_keypair,
    rsa_decrypt_real,
    rsa_encrypt_real,
    rsa_sign_real,
    rsa_verify_real,
)


def test_keygen_produces_valid_pem():
    keys = generate_rsa_keypair(2048)
    assert keys["key_size"] == 2048
    assert "BEGIN PRIVATE KEY" in keys["private_key_pem"]
    assert "BEGIN PUBLIC KEY" in keys["public_key_pem"]


def test_encrypt_decrypt_roundtrip():
    keys = generate_rsa_keypair(2048)
    message = "TrueMath test message with unicode: café"
    ciphertext = rsa_encrypt_real(message, keys["public_key_pem"])
    plaintext = rsa_decrypt_real(ciphertext, keys["private_key_pem"])
    assert plaintext == message


def test_sign_verify():
    keys = generate_rsa_keypair(2048)
    message = "sign this"
    signature = rsa_sign_real(message, keys["private_key_pem"])
    assert rsa_verify_real(message, signature, keys["public_key_pem"]) is True
    # Tampered message must fail verification
    assert rsa_verify_real("sign this (tampered)", signature, keys["public_key_pem"]) is False


def test_invalid_key_size_rejected():
    import pytest
    with pytest.raises(ValueError):
        generate_rsa_keypair(1024)  # below the accepted real-security sizes
