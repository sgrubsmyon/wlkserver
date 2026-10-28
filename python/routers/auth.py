import time
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import select

from ..dependencies import require_admin, require_user
from ..models import Anmeldung, AnmeldungPublic, User, UserPublic
from ..session import SessionDep
from ..utils.auth import verify_password, create_token, decode_token

router = APIRouter(prefix="/auth", tags=["auth"])

bearer_scheme = HTTPBearer(auto_error=False)

from pydantic import BaseModel


class LoginPayload(BaseModel):
    username: str
    password: str


# Failed-login throttling (in-memory; the API runs as a single worker).
LOGIN_MAX_FAILURES = 5
LOGIN_WINDOW_SECONDS = 60
_login_failures: dict[str, list[float]] = {}


def _login_key(request: Request, username: str) -> str:
    host = request.client.host if request.client else "unknown"
    return f"{host}:{username}"


def _check_login_rate(key: str) -> None:
    now = time.monotonic()
    attempts = [t for t in _login_failures.get(key, []) if now - t < LOGIN_WINDOW_SECONDS]
    _login_failures[key] = attempts
    if len(attempts) >= LOGIN_MAX_FAILURES:
        raise HTTPException(status_code=429, detail="Too many login attempts, try again later")


def _extract_token(credentials: Optional[HTTPAuthorizationCredentials], token: Optional[str]) -> Optional[str]:
    if credentials is not None and credentials.credentials:
        return credentials.credentials
    return token


@router.post("/login")
def login(payload: LoginPayload, session: SessionDep, request: Request):
    key = _login_key(request, payload.username)
    _check_login_rate(key)
    user = session.exec(select(User).where(User.username == payload.username)).first()
    if not user or not user.active or not verify_password(payload.password, user.password_hash):
        _login_failures.setdefault(key, []).append(time.monotonic())
        raise HTTPException(status_code=401, detail="Invalid credentials")
    _login_failures.pop(key, None)
    anmeldung = Anmeldung(user_id=user.user_id, login_time=datetime.now(timezone.utc))
    anmeldung.anmeldung_id = None
    session.add(anmeldung)
    session.commit()
    session.refresh(anmeldung)
    token = create_token({"user_id": user.user_id, "username": user.username, "role": user.role, "anmeldung_id": anmeldung.anmeldung_id})
    return {"access_token": token, "token_type": "bearer", "user": UserPublic.model_validate(user).model_dump()}


@router.post("/refresh")
def refresh(credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)] = None, user: User = Depends(require_user)):
    payload = decode_token(credentials.credentials) if credentials else None
    claims = {"user_id": user.user_id, "username": user.username, "role": user.role}
    if payload and payload.get("anmeldung_id") is not None:
        claims["anmeldung_id"] = payload["anmeldung_id"]
    return {"access_token": create_token(claims), "token_type": "bearer"}


@router.get("/anmeldungen", response_model=list[AnmeldungPublic])
def read_anmeldungen(
    session: SessionDep,
    user_id: Optional[int] = None,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
    _admin: User = Depends(require_admin),
) -> list[AnmeldungPublic]:
    selection = select(Anmeldung)
    if user_id is not None:
        selection = selection.where(Anmeldung.user_id == user_id)
    rows = session.exec(
        selection.offset(offset).limit(limit).order_by(Anmeldung.login_time.desc())
    ).all()
    return [AnmeldungPublic.model_validate(a) for a in rows]


@router.post("/logout")
def logout(session: SessionDep, credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)] = None, token: Optional[str] = Query(default=None)):
    t = _extract_token(credentials, token)
    if t is None:
        return {"message": "logged out"}
    payload = decode_token(t)
    if payload and payload.get("anmeldung_id") is not None:
        a = session.get(Anmeldung, payload["anmeldung_id"])
        if a and a.logout_time is None:
            a.logout_time = datetime.now(timezone.utc)
            session.add(a)
            session.commit()
    return {"message": "logged out"}


@router.get("/me")
def me(user: User = Depends(require_user)):
    return UserPublic.model_validate(user).model_dump()


# aliases
login_user = login
logout_user = logout
get_me = me
refresh_token = refresh
