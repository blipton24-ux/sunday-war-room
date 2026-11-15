"""Encrypting stored platform credentials: ESPN cookies now, Yahoo tokens later (ADR-052).

The API encrypts before saving and decrypts only inside the worker or request that needs the
value. `CREDENTIALS_KEYS` holds one or more Fernet keys: the first encrypts, every key can
decrypt, so a new key is added at the front and old rows are re-encrypted with `rotate`.

A leaked database backup alone is gibberish. An attacker who controls the running server can
read the key too; no scheme protects against that.
"""

from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from app.config import get_settings


class CredentialError(Exception):
    """A stored credential could not be decrypted (wrong key, or the data was altered)."""


class CredentialCipher:
    def __init__(self, keys: Sequence[str]) -> None:
        if not keys:
            raise ValueError("at least one credentials key is required")
        self._fernet = MultiFernet([Fernet(k) for k in keys])

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken as exc:
            raise CredentialError("stored credential could not be decrypted") from exc

    def rotate(self, token: str) -> str:
        """Re-encrypt `token` with the newest key (reads with any listed key)."""
        try:
            return self._fernet.rotate(token.encode()).decode()
        except InvalidToken as exc:
            raise CredentialError("stored credential could not be decrypted") from exc


@lru_cache
def get_cipher() -> CredentialCipher:
    return CredentialCipher(get_settings().credentials_key_list)
