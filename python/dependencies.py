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
