from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select

from ..models import User, UserPublic, UserCreate, UserUpdate
from ..session import SessionDep
from ..dependencies import require_admin
from ..utils.auth import hash_password

router = APIRouter(prefix="/users", tags=["users"], responses={404: {"description": "Not found"}})


@router.get("/")
def read_users(
    session: SessionDep,
    role: str = "",
    active: Optional[bool] = None,
    search_string: str = "",
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> list[UserPublic]:
    selection = select(User)
    if role:
        selection = selection.where(User.role == role)
    if active is not None:
        selection = selection.where(User.active == active)
    for term in search_string.split():
        selection = selection.where(User.username.contains(term))
    users = session.exec(
        selection.offset(offset).limit(limit).order_by(User.username)
    ).all()
    return [UserPublic.model_validate(u) for u in users]


@router.get("/{user_id}")
def read_user(user_id: int, session: SessionDep) -> UserPublic:
    u = session.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return UserPublic.model_validate(u)


@router.post("/", response_model=UserPublic)
def create_user(user: UserCreate, session: SessionDep, _admin=Depends(require_admin)):
    existing = session.exec(select(User).where(User.username == user.username)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    new_u = User(
        username=user.username,
        password_hash=hash_password(user.password),
        role=user.role,
        active=user.active,
    )
    new_u.user_id = None
    session.add(new_u)
    session.commit()
    session.refresh(new_u)
    return UserPublic.model_validate(new_u)


@router.patch("/{user_id}", response_model=UserPublic)
def update_user(user_id: int, user: UserUpdate, session: SessionDep, _admin=Depends(require_admin)):
    u = session.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    if user.username is not None:
        u.username = user.username
    if user.role is not None:
        u.role = user.role
    if user.active is not None:
        u.active = user.active
    if user.password is not None:
        u.password_hash = hash_password(user.password)
    session.add(u)
    session.commit()
    session.refresh(u)
    return UserPublic.model_validate(u)


@router.post("/{user_id}/deactivate", response_model=UserPublic)
def deactivate_user(user_id: int, session: SessionDep, _admin=Depends(require_admin)):
    u = session.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u.active = False
    session.add(u)
    session.commit()
    session.refresh(u)
    return UserPublic.model_validate(u)


@router.post("/{user_id}/reset-password", response_model=UserPublic)
def reset_password(user_id: int, session: SessionDep, new_password: str = Query(...), _admin=Depends(require_admin)):
    u = session.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u.password_hash = hash_password(new_password)
    session.add(u)
    session.commit()
    session.refresh(u)
    return UserPublic.model_validate(u)


# aliases
read_user_by_id = read_user
create_user_entry = create_user
update_user_entry = update_user
