"""
Module Name: real_crypto
Purpose: PRODUCTION-GRADE cryptography — real security, using the audited
         `cryptography` library (OpenSSL-backed), not hand-rolled math.
Responsibilities:
  - Generate real RSA keypairs (2048/3072/4096-bit, industry-standard
    sizes) with proper key generation (secure randomness via the OS CSPRNG).
  - Encrypt/decrypt using OAEP padding (the correct, secure RSA padding
    scheme — raw/textbook RSA without padding, like crypto_math.py's toy
    version, is NOT secure even at large key sizes, because it's malleable
    and deterministic).
  - Sign/verify using PSS padding (the correct, secure RSA signature scheme).
  - Export/import keys in standard PEM format, so they work with any other
    real crypto tool (openssl, other languages, etc.).
Dependencies: cryptography (pip install cryptography — wraps OpenSSL)
Honesty note: This is genuinely secure, production-usable cryptography —
              the same library used by major Python projects (Django,
              requests, etc.) for real TLS/crypto needs. The difference
              from crypto_math.py's rsa_toy_keygen is not just bit-size:
              real security also requires correct padding (OAEP/PSS), which
              textbook RSA math alone does not provide. Never use raw
              modular exponentiation (m^e mod n) directly on real data —
              that's what crypto_math.py's toy version does, and it is
              insecure regardless of key size (no padding = malleable,
              deterministic, vulnerable to several classic attacks).
"""
from __future__ import annotations

import base64
from typing import Dict

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

_VALID_KEY_SIZES = (2048, 3072, 4096)


def generate_rsa_keypair(key_size: int = 2048) -> Dict[str, str]:
    """Generates a REAL RSA keypair at a real security-strength size.
    2048-bit is the current minimum recommended size (NIST); 3072/4096
    give more long-term margin. Returns PEM-encoded keys (standard format,
    usable with any other crypto tool/language)."""
    if key_size not in _VALID_KEY_SIZES:
        raise ValueError(f"key_size must be one of {_VALID_KEY_SIZES} for real security.")

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    return {
        "key_size": key_size,
        "private_key_pem": private_pem,
        "public_key_pem": public_pem,
        "note": f"Real {key_size}-bit RSA keypair with OAEP padding — genuinely secure, not a demo.",
    }


def rsa_encrypt_real(message: str, public_key_pem: str) -> str:
    """Encrypts a UTF-8 string with real RSA-OAEP (SHA-256). Returns
    base64-encoded ciphertext. Note: RSA can only encrypt messages shorter
    than the key size minus padding overhead (~190 bytes for a 2048-bit
    key) — for larger data, real systems encrypt a random AES key with RSA
    and the actual data with AES (hybrid encryption), same as TLS does."""
    public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
    ciphertext = public_key.encrypt(
        message.encode("utf-8"),
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
    )
    return base64.b64encode(ciphertext).decode("ascii")


def rsa_decrypt_real(ciphertext_b64: str, private_key_pem: str) -> str:
    """Decrypts base64-encoded RSA-OAEP ciphertext back to the original
    UTF-8 string."""
    private_key = serialization.load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
    ciphertext = base64.b64decode(ciphertext_b64)
    plaintext = private_key.decrypt(
        ciphertext,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
    )
    return plaintext.decode("utf-8")


def rsa_sign_real(message: str, private_key_pem: str) -> str:
    """Signs a message with real RSA-PSS (SHA-256) — the secure, standard
    RSA signature scheme. Returns base64-encoded signature."""
    private_key = serialization.load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
    signature = private_key.sign(
        message.encode("utf-8"),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("ascii")


def rsa_verify_real(message: str, signature_b64: str, public_key_pem: str) -> bool:
    """Verifies an RSA-PSS signature. Returns True if valid, False if the
    signature doesn't match (never raises for a bad signature — that's the
    expected, common outcome, not an error)."""
    public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
    signature = base64.b64decode(signature_b64)
    try:
        public_key.verify(
            signature,
            message.encode("utf-8"),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False
