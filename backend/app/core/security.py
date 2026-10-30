from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import get_settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(
    *, sub: str, role: str, bank_name: str | None = None, institution_id: int | None = None
) -> tuple[str, int]:
    settings = get_settings()
    expire_minutes = settings.JWT_EXPIRE_MINUTES
    # JWT exp/iat are intentionally real wall-clock time, not the simulated business clock:
    # PyJWT validates `exp` against the real system clock regardless of what we pass it, so
    # basing it on the simulated date (which can sit far from real "now") would make tokens
    # expire immediately or never. Session lifetime is an auth/infra concern, not domain data.
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    claims: dict[str, Any] = {
        "sub": sub,
        "role": role,
        "exp": expires_at,
    }
    if bank_name is not None:
        claims["bank_name"] = bank_name
    if institution_id is not None:
        claims["institution_id"] = institution_id
    token = jwt.encode(claims, settings.JWT_SECRET, algorithm=ALGORITHM)
    return token, expire_minutes * 60


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
