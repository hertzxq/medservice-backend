"""
Security utilities: JWT tokens and password hashing.
Uses python-jose for JWT and bcrypt for password hashing.
"""

from datetime import datetime, timedelta
import hashlib
import hmac
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from app.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        plain_password: Plain text password
        hashed_password: Bcrypt hashed password

    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except ValueError:
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Bcrypt hashed password
    """
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload data to encode (typically {"sub": user_id})
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def _password_reset_fingerprint(hashed_password: str) -> str:
    """Secret-keyed fingerprint used to invalidate reset tokens after password changes."""
    return hmac.new(
        settings.secret_key.encode("utf-8"),
        hashed_password.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_password_reset_token(
    user_id: int,
    hashed_password: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a short-lived JWT for password reset."""
    expire = datetime.utcnow() + (
        expires_delta
        if expires_delta
        else timedelta(minutes=settings.password_reset_token_expire_minutes)
    )
    payload = {
        "sub": str(user_id),
        "purpose": "password_reset",
        "pwd": _password_reset_fingerprint(hashed_password),
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_password_reset_token(token: str) -> Optional[dict]:
    """Decode a password reset token and reject tokens created for other purposes."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None

    if payload.get("purpose") != "password_reset":
        return None

    return payload


def verify_password_reset_token_fingerprint(
    token_fingerprint: str | None,
    hashed_password: str,
) -> bool:
    """Check that a reset token still matches the user's current password hash."""
    if not token_fingerprint:
        return False

    expected = _password_reset_fingerprint(hashed_password)
    return hmac.compare_digest(token_fingerprint, expected)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT access token.

    Args:
        token: JWT token string

    Returns:
        Decoded payload dict if valid, None if invalid
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None
