"""Authentication utilities (bcrypt + PyJWT)."""
from __future__ import annotations

import secrets
import time
from typing import Any, Optional

import bcrypt
import jwt

from .. import config

TOKEN_SECRET = config.auth_secret()
TOKEN_TTL = config.auth_token_ttl()

ALGO = "HS256"


def hash_password(password: str, salt: Optional[str] = None) -> str:
    # salt is ignored (bcrypt manages its own salt); kept for API compatibility
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        # Backwards compatibility with legacy pbkdf2 hashes
        if password_hash.startswith("pbkdf2_sha256$"):
            try:
                import hashlib, hmac
                _, salt, digest = password_hash.split("$", 2)
                dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
                return hmac.compare_digest(dk.hex(), digest)
            except Exception:
                return False
        return False


def create_token(payload: dict[str, Any], ttl: int = TOKEN_TTL) -> str:
    body = dict(payload)
    now = int(time.time())
    body.setdefault("iat", now)
    body.setdefault("exp", now + ttl)
    return jwt.encode(body, TOKEN_SECRET, algorithm=ALGO)


def decode_token(token: str) -> Optional[dict[str, Any]]:
    try:
        return jwt.decode(token, TOKEN_SECRET, algorithms=[ALGO])
    except Exception:
        return None


def generate_token(*args, **kwargs):
    # compatibility: allow create_token alias
    return create_token(*args, **kwargs)
