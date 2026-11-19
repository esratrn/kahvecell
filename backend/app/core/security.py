import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.core.config import settings


def hash_secret(value: str) -> str:
    return hmac.new(
        settings.jwt_secret_key.encode(), value.encode(), hashlib.sha256
    ).hexdigest()


def secrets_match(raw_value: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_secret(raw_value), stored_hash)


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def create_access_token(user_id: uuid.UUID, role: str) -> tuple[str, int]:
    now = datetime.now(timezone.utc)
    lifetime = timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + lifetime,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, int(lifetime.total_seconds())


def decode_access_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["exp", "sub", "type"]},
    )
    if payload["type"] != "access":
        raise jwt.InvalidTokenError("Not an access token")
    return payload
