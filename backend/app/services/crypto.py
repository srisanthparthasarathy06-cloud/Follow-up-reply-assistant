"""
Encrypts/decrypts OAuth tokens before they touch the database. Never store
an access or refresh token in plaintext.

Uses Fernet (symmetric, authenticated encryption) keyed by TOKEN_ENCRYPTION_KEY.
Generate a key with:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def _get_fernet() -> Fernet:
    if not settings.token_encryption_key:
        raise RuntimeError(
            "TOKEN_ENCRYPTION_KEY is not set in .env — generate one with "
            "`python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"` "
            "and add it before connecting an email account."
        )
    return Fernet(settings.token_encryption_key.encode())


def encrypt(value: str) -> str:
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    try:
        return _get_fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise RuntimeError("Stored token could not be decrypted — TOKEN_ENCRYPTION_KEY may have changed.") from exc
