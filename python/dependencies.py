"""Authorization dependencies."""
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .models import Anmeldung, User
from .session import SessionDep
from .utils.auth import decode_token

load_dotenv()

bearer_scheme = HTTPBearer(auto_error=False)

CredentialsDep = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


def get_current_user(session: SessionDep, credentials: CredentialsDep = None) -> User | None:
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
    anmeldung_id = payload.get("anmeldung_id")
    if anmeldung_id is not None:
        anmeldung = session.get(Anmeldung, anmeldung_id)
        if not anmeldung or anmeldung.user_id != user.user_id or anmeldung.logout_time is not None:
            return None
    return user


def require_user(session: SessionDep, credentials: CredentialsDep = None) -> User:
    user = get_current_user(session, credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(session: SessionDep, credentials: CredentialsDep = None) -> User:
    user = require_user(session, credentials)
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user
