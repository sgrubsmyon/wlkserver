from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select

from ..models import User, Anmeldung, UserPublic
from ..session import SessionDep
from ..utils.auth import verify_password, create_token, decode_token, hash_password

router = APIRouter(prefix="/auth", tags=["auth"])


from pydantic import BaseModel


class LoginPayload(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(payload: LoginPayload, session: SessionDep):
    user = session.exec(select(User).where(User.username == payload.username)).first()
    if not user or not user.active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    anmeldung = Anmeldung(user_id=user.user_id, login_time=datetime.now(timezone.utc))
    anmeldung.anmeldung_id = None
    session.add(anmeldung)
    session.commit()
    session.refresh(anmeldung)
    token = create_token({"user_id": user.user_id, "username": user.username, "role": user.role, "anmeldung_id": anmeldung.anmeldung_id})
    return {"access_token": token, "token_type": "bearer", "user": UserPublic.model_validate(user).model_dump()}


@router.post("/logout")
def logout(session: SessionDep, token: Optional[str] = Query(default=None)):
    # token may be passed as query or header; try query only for simplicity
    if token is None:
        return {"message": "logged out"}
    payload = decode_token(token)
    if payload and payload.get("anmeldung_id") is not None:
        a = session.get(Anmeldung, payload["anmeldung_id"])
        if a and a.logout_time is None:
            a.logout_time = datetime.now(timezone.utc)
            session.add(a)
            session.commit()
    return {"message": "logged out"}


@router.get("/me")
def me(session: SessionDep, token: Optional[str] = Query(default=None)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = session.get(User, payload.get("user_id"))
    if not user or not user.active:
        raise HTTPException(status_code=401, detail="User not found")
    return UserPublic.model_validate(user).model_dump()


# aliases
login_user = login
logout_user = logout
get_me = me
