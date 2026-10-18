"""
Authorization dependencies.

Temporary stopgap until the per-user account system from Phase 7.4
(user table, JWT sessions, roles) is implemented: admin-only endpoints
are protected by a shared admin token from the ADMIN_TOKEN environment
variable, sent as `Authorization: Bearer <ADMIN_TOKEN>`.
Fails closed: if ADMIN_TOKEN is not set, admin endpoints are unavailable.
"""
import os
import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from dotenv import load_dotenv

load_dotenv()

bearer_scheme = HTTPBearer(auto_error=False)

CredentialsDep = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


def require_admin(credentials: CredentialsDep = None):
    admin_token = os.getenv("ADMIN_TOKEN")
    if not admin_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin authentication is not configured (set ADMIN_TOKEN in the environment)",
        )
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not secrets.compare_digest(credentials.credentials, admin_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin token",
        )


# --- Phase 7.4: per-user auth helpers ---

import os
from typing import Optional

from sqlmodel import select
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials

from .utils.auth import decode_token
from .models import User
from .session import SessionDep


def get_current_user(session: SessionDep, credentials: CredentialsDep = None) -> Optional[User]:
    if credentials is None:
        return None
    payload = decode_token(credentials.credentials)
    if not payload:
        return None
    user_id = payload.get("user_id")
    if user_id is None:
        return None
    user = session.get(User, user_id)
    if not user or not user.active:
        return None
    return user


def require_user(session: SessionDep, credentials: CredentialsDep = None) -> User:
    user = get_current_user(session, credentials)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    return user


def require_admin_user(session: SessionDep, credentials: CredentialsDep = None) -> User:
    # allow admin token OR admin user
    admin_token = os.getenv("ADMIN_TOKEN")
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    if admin_token and secrets.compare_digest(credentials.credentials, admin_token):
        return None  # type: ignore
    user = get_current_user(session, credentials)
    if user is not None and user.role == "admin":
        return user
    if not admin_token:
        raise HTTPException(status_code=503, detail="Admin authentication is not configured")
    raise HTTPException(status_code=403, detail="Invalid admin token")


# Override require_admin to also accept admin JWTs
_original_require_admin = require_admin


def require_admin(credentials: CredentialsDep = None):
    admin_token = os.getenv("ADMIN_TOKEN")
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    if admin_token and secrets.compare_digest(credentials.credentials, admin_token):
        return None
    payload = decode_token(credentials.credentials)
    if payload and payload.get("role") == "admin":
        return None
    if not admin_token:
        raise HTTPException(status_code=503, detail="Admin authentication is not configured (set ADMIN_TOKEN in the environment)")
    raise HTTPException(status_code=403, detail="Invalid admin token")
