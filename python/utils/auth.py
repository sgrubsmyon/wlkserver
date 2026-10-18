"""Authentication utilities (stdlib-only)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any, Optional

TOKEN_SECRET = os.getenv("AUTH_SECRET", os.getenv("SECRET_KEY", "dev-secret-change-me"))
TOKEN_TTL = int(os.getenv("AUTH_TOKEN_TTL", "3600"))

ALGO = "HS256"


def hash_password(password: str, salt: Optional[str] = None) -> str:
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"pbkdf2_sha256${salt}${dk.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, salt, digest = password_hash.split("$", 2)
    except ValueError:
        return False
    if scheme != "pbkdf2_sha256":
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return hmac.compare_digest(dk.hex(), digest)


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def create_token(payload: dict[str, Any], ttl: int = TOKEN_TTL) -> str:
    body = dict(payload)
    body["iat"] = int(time.time())
    body["exp"] = int(time.time()) + ttl
    raw = json.dumps(body, separators=(",", ":")).encode()
    sig = hmac.new(TOKEN_SECRET.encode(), raw, hashlib.sha256).digest()
    return _b64encode(raw) + "." + _b64encode(sig)


def decode_token(token: str) -> Optional[dict[str, Any]]:
    try:
        raw_b64, sig_b64 = token.split(".", 1)
        raw = _b64decode(raw_b64)
        sig = _b64decode(sig_b64)
    except Exception:
        return None
    expected = hmac.new(TOKEN_SECRET.encode(), raw, hashlib.sha256).digest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        payload = json.loads(raw)
    except Exception:
        return None
    if payload.get("exp", 0) < time.time():
        return None
    return payload


def generate_token(*args, **kwargs):
    # compatibility: allow create_token alias
    return create_token(*args, **kwargs)
