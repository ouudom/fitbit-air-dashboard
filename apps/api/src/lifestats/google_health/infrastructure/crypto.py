import base64
import hashlib
import json
import os

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.padding import PKCS7


def _urlsafe_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class TokenCipher:
    def __init__(self, secret: str, laravel_app_key: str = "") -> None:
        if not secret:
            raise RuntimeError("TOKEN_ENCRYPTION_KEY is required")
        self.key = hashlib.sha256(secret.encode()).digest()
        self.laravel_app_key = laravel_app_key

    def encrypt(self, value: str | None) -> str | None:
        if not value:
            return value
        nonce = os.urandom(12)
        encoded = base64.urlsafe_b64encode(
            nonce + AESGCM(self.key).encrypt(nonce, value.encode(), None)
        )
        return "enc:v2:" + encoded.decode().rstrip("=")

    def decrypt(self, value: str | None) -> str | None:
        if not value:
            return value
        if value.startswith("enc:v2:"):
            raw = _urlsafe_decode(value[7:])
            return AESGCM(self.key).decrypt(raw[:12], raw[12:], None).decode()
        if value.startswith("enc:v1:"):
            raw = _urlsafe_decode(value[7:])
            return AESGCM(self.key).decrypt(raw[:12], raw[28:] + raw[12:28], None).decode()
        try:
            return self._decrypt_laravel(value)
        except Exception:
            return value

    def _decrypt_laravel(self, value: str) -> str:
        if not self.laravel_app_key:
            raise ValueError("No Laravel key")
        raw_key = self.laravel_app_key.removeprefix("base64:")
        key = (
            base64.b64decode(raw_key)
            if self.laravel_app_key.startswith("base64:")
            else raw_key.encode()
        )
        payload = json.loads(base64.b64decode(value))
        iv = base64.b64decode(payload["iv"])
        encrypted = base64.b64decode(payload["value"])
        if payload.get("tag"):
            tag = base64.b64decode(payload["tag"])
            gcm_decryptor = Cipher(algorithms.AES(key), modes.GCM(iv, tag)).decryptor()
            return (gcm_decryptor.update(encrypted) + gcm_decryptor.finalize()).decode()
        cbc_decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
        padded = cbc_decryptor.update(encrypted) + cbc_decryptor.finalize()
        unpadder = PKCS7(128).unpadder()
        return (unpadder.update(padded) + unpadder.finalize()).decode()
