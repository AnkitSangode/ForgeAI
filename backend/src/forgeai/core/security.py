from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from forgeai.core.config import get_settings

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Generate a secure password hash."""

    if not password:
        raise ValueError("Password cannot be empty.")

    return password_hasher.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """Verify a password against its stored hash."""

    if not plain_password or not hashed_password:
        return False

    return password_hasher.verify(
        plain_password,
        hashed_password,
    )


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token for an authenticated user."""

    if not subject or not subject.strip():
        raise ValueError("Token subject cannot be empty.")

    settings = get_settings()

    now = datetime.now(UTC)
    expires_at = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.access_token_expire_minutes)
    )

    payload = {
        "sub": subject,
        "iat": now,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict:
    """Verify a JWT and return its validated claims."""

    if not token:
        raise jwt.InvalidTokenError("Access token is required.")

    settings = get_settings()

    return jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
        options={
            "require": ["sub", "iat", "exp"],
        },
    )
