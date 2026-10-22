import base64
import json
import logging
import math
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import bcrypt
import jwt

from app.core.config import settings

# Bounded tolerance for small clock corrections; signature/audience checks remain enabled.
JWT_CLOCK_SKEW_SECONDS = 2
logger = logging.getLogger(__name__)
_CLOCK_WALL, _CLOCK_MONO = time.time(), time.monotonic()


def _clock_metadata(token: str) -> dict:
    """Numeric timing only, never authorization data. Do not log token or full claims."""
    wall = time.time()
    result = {
        "server_unix": wall,
        "utc_minus_wall_seconds": datetime.now(timezone.utc).timestamp() - wall,
        "wall_vs_monotonic_delta_seconds": (wall - _CLOCK_WALL) - (time.monotonic() - _CLOCK_MONO),
    }
    # Bound diagnostic parsing independently of the authentication parser.
    try:
        encoded = token.split(".")[1]
        if len(encoded) > 8192:
            return result
        claims = json.loads(base64.urlsafe_b64decode(encoded + "==="))
        for name in ("iat", "nbf"):
            value = claims.get(name)
            if type(value) in (int, float) and math.isfinite(value) and abs(value) <= 10**12:
                result[name + "_ahead_seconds"] = value - wall
    except (ValueError, TypeError, AttributeError, IndexError, OverflowError):
        pass  # Diagnostics must never replace the original authentication failure.
    return result


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: uuid.UUID, tenant_id: uuid.UUID, role: str, auth_version: int = 0) -> str:
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role,
        "ver": auth_version,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Raise jwt.PyJWTError nếu token sai/hết hạn."""
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM], leeway=JWT_CLOCK_SKEW_SECONDS)
    except jwt.ImmatureSignatureError:
        # Observation only: strict verification still rejects this request.
        logger.warning("Authentication clock validation rejected (ImmatureSignatureError): %s", _clock_metadata(token))
        raise
