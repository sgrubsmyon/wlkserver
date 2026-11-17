"""Admin user management endpoints.

Writes require an admin. Accounts can be deactivated instead of deleted; a
delete is refused for the own account, for the last active admin and for users
that bookkeeping rows still reference.
"""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from ..models import User
from ..schemas import (
    UserPublic,
    UserCreate,
    UserUpdate,
)
from ..session import SessionDep
from ..dependencies import require_admin
from ..utils.auth import hash_password
from ..utils.pagination import paginate

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
    """List users with role, active and name filters."""
    selection = select(User)
    if role:
        selection = selection.where(User.role == role)
    if active is not None:
        selection = selection.where(User.active == active)
    for term in search_string.split():
        selection = selection.where(User.username.contains(term))
    users = paginate(session, selection, offset, limit, User.username)
    return [UserPublic.model_validate(u) for u in users]


@router.get("/{user_id}")
def read_user(user_id: int, session: SessionDep) -> UserPublic:
    """Read one user by id; 404 if unknown."""
    u = session.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return UserPublic.model_validate(u)


@router.post("/", response_model=UserPublic)
def create_user(user: UserCreate, session: SessionDep, _admin=Depends(require_admin)):
    """Create a user with a hashed password (admin only); 400 if the name is taken."""
    existing = session.exec(select(User).where(User.username == user.username)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    new_u = User(
        username=user.username,
        password_hash=hash_password(user.password),
        role=user.role,
        active=user.active,
        full_name=user.full_name,
        pref_theme=user.pref_theme,
    )
    new_u.user_id = None
    session.add(new_u)
    session.commit()
    session.refresh(new_u)
    return UserPublic.model_validate(new_u)


@router.patch("/{user_id}", response_model=UserPublic)
def update_user(user_id: int, user: UserUpdate, session: SessionDep, _admin=Depends(require_admin)):
    """Update user fields, hashing a new password if one is given (admin only)."""
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
    if user.full_name is not None:
        u.full_name = user.full_name
    if user.pref_theme is not None:
        u.pref_theme = user.pref_theme
    session.add(u)
    session.commit()
    session.refresh(u)
    return UserPublic.model_validate(u)


@router.post("/{user_id}/deactivate", response_model=UserPublic)
def deactivate_user(user_id: int, session: SessionDep, _admin=Depends(require_admin)):
    """Deactivate a user account (admin only)."""
    u = session.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u.active = False
    session.add(u)
    session.commit()
    session.refresh(u)
    return UserPublic.model_validate(u)


@router.delete("/{user_id}")
def delete_user(user_id: int, session: SessionDep, admin: User = Depends(require_admin)):
    """Delete an account. Self-deletion and removing the last admin are refused."""
    u = session.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    if u.user_id == admin.user_id:
        raise HTTPException(status_code=400, detail="Cannot delete the own account")
    if u.role == "admin" and u.active:
        remaining = session.exec(
            select(User).where(User.role == "admin", User.active == True,
                               User.user_id != user_id)
        ).all()
        if not remaining:
            raise HTTPException(status_code=400, detail="Cannot delete the last active admin")
    try:
        session.delete(u)
        session.commit()
    except IntegrityError:
        # Bookkeeping references (sales, logins, ...) must not be orphaned.
        session.rollback()
        raise HTTPException(
            status_code=400,
            detail="User has transactions and cannot be deleted; deactivate instead",
        )
    return {"message": "User deleted"}


@router.post("/{user_id}/reset-password", response_model=UserPublic)
def reset_password(user_id: int, session: SessionDep, new_password: str = Query(...), _admin=Depends(require_admin)):
    """Set a new password for a user without the old one (admin only)."""
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
