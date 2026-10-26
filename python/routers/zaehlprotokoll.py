from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from ..models import (
    Zaehlprotokoll,
    ZaehlprotokollPublic,
    ZaehlprotokollCreate,
    ZaehlprotokollUpdate,
    ZaehlprotokollDetails,
    ZaehlprotokollDetailsPublic,
    ZaehlprotokollDetailsCreate,
    AbrechnungTag,
)
from ..session import SessionDep
from ..dependencies import bearer_scheme, require_user
from fastapi.security import HTTPAuthorizationCredentials
from fastapi import Depends

router = APIRouter(
    prefix="/zaehlprotokoll",
    tags=["zaehlprotokoll"],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
def read_zaehlprotokolle(
    session: SessionDep,
    abrechnung_tag_id: Optional[int] = None,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> list[ZaehlprotokollPublic]:
    selection = select(Zaehlprotokoll)
    if abrechnung_tag_id is not None:
        selection = selection.where(Zaehlprotokoll.abrechnung_tag_id == abrechnung_tag_id)
    rows = session.exec(
        selection.offset(offset).limit(limit).order_by(Zaehlprotokoll.id)
    ).all()
    return [ZaehlprotokollPublic.model_validate(r) for r in rows]


@router.get("/abrechnung/{abrechnung_tag_id}")
def read_zaehlprotokolle_fuer_abrechnung(abrechnung_tag_id: int, session: SessionDep) -> list[ZaehlprotokollPublic]:
    rows = session.exec(
        select(Zaehlprotokoll).where(Zaehlprotokoll.abrechnung_tag_id == abrechnung_tag_id)
    ).all()
    return [ZaehlprotokollPublic.model_validate(r) for r in rows]


@router.get("/{zp_id}")
def read_single_zaehlprotokoll(zp_id: int, session: SessionDep) -> ZaehlprotokollPublic:
    zp = session.get(Zaehlprotokoll, zp_id)
    if not zp:
        raise HTTPException(status_code=404, detail="Zaehlprotokoll not found")
    return ZaehlprotokollPublic.model_validate(zp)


@router.post("/", response_model=ZaehlprotokollPublic)
def create_zaehlprotokoll(zp: ZaehlprotokollCreate, session: SessionDep, credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme), _user=Depends(require_user)):
    user_id = None
    if credentials is not None and credentials.credentials:
        from ..utils.auth import decode_token
        tok = decode_token(credentials.credentials)
        if tok:
            user_id = tok.get("user_id")
    abr = session.get(AbrechnungTag, zp.abrechnung_tag_id)
    if not abr:
        raise HTTPException(status_code=400, detail="AbrechnungTag not found")
    new_zp = Zaehlprotokoll(
        abrechnung_tag_id=zp.abrechnung_tag_id,
        zeitpunkt=zp.zeitpunkt if zp.zeitpunkt is not None else datetime.now(timezone.utc),
        kommentar=zp.kommentar,
        aktiv=zp.aktiv,
        user_id=user_id,
    )
    new_zp.id = None
    session.add(new_zp)
    session.commit()
    session.refresh(new_zp)
    for d in (zp.details or []):
        dd = ZaehlprotokollDetails(
            zaehlprotokoll_id=new_zp.id,
            anzahl=d.anzahl,
            einheit=d.einheit,
        )
        dd.id = None
        session.add(dd)
    if zp.details:
        session.commit()
    return ZaehlprotokollPublic.model_validate(new_zp)


@router.patch("/{zp_id}", response_model=ZaehlprotokollPublic)
def update_zaehlprotokoll(zp_id: int, zp: ZaehlprotokollUpdate, session: SessionDep, _user=Depends(require_user)):
    old = session.get(Zaehlprotokoll, zp_id)
    if not old:
        raise HTTPException(status_code=404, detail="Zaehlprotokoll not found")
    data = zp.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(old, key, value)
    session.add(old)
    session.commit()
    session.refresh(old)
    return ZaehlprotokollPublic.model_validate(old)


# Aliases
read_zaehlprotokoll = read_zaehlprotokolle
read_zaehlprotokolle_alias = read_zaehlprotokolle
create_zaehlprotokoll_entry = create_zaehlprotokoll