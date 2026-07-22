import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from lifestats.google_health.infrastructure.crypto import TokenCipher


def test_v2_round_trip() -> None:
    cipher = TokenCipher("secret")
    encrypted = cipher.encrypt("health-token")
    assert encrypted and encrypted.startswith("enc:v2:")
    assert cipher.decrypt(encrypted) == "health-token"


def test_legacy_v1_compatibility() -> None:
    secret = "legacy-secret"
    key = hashlib.sha256(secret.encode()).digest()
    nonce = os.urandom(12)
    encrypted = AESGCM(key).encrypt(nonce, b"legacy-token", None)
    body, tag = encrypted[:-16], encrypted[-16:]
    value = "enc:v1:" + base64.urlsafe_b64encode(nonce + tag + body).decode().rstrip("=")
    assert TokenCipher(secret).decrypt(value) == "legacy-token"
