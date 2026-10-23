"""Training mode endpoints.

The Java POS switches between normal and training operation mode and writes all
cashier transactions to the `training_*` tables (`tableForMode()` in
`WindowContent.java`). The API exposes the core training flow explicitly: a
training sale is written to `training_verkauf`, `training_verkauf_details`,
`training_verkauf_mwst` and (for cash payments) `training_kassenstand`.
"""
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import SQLModel, select

from ..models import (
    Artikel,
    TrainingKassenstand,
    TrainingVerkauf,
    TrainingVerkaufDetails,
    TrainingVerkaufMwst,
    VerkaufDetailsCreate,
)
from ..session import SessionDep
from ..dependencies import require_user
from ..business.cash_register import is_training_mode
from ..business.sale_workflow import prepare_detail, calculate_mwst_summary, validate_detail

router = APIRouter(
    prefix="/training",
    tags=["training"],
    responses={404: {"description": "Not found"}},
)


class TrainingVerkaufCreate(SQLModel):
    ec_zahlung: bool = False
    kunde_gibt: float | None = None
    verkauf_details: list[VerkaufDetailsCreate] | None = None


def _sale_dict(v: TrainingVerkauf, session: SessionDep) -> dict:
    details = session.exec(
        select(TrainingVerkaufDetails)
        .where(TrainingVerkaufDetails.rechnungs_nr == v.rechnungs_nr)
        .order_by(TrainingVerkaufDetails.position)
    ).all()
    mwsts = session.exec(
        select(TrainingVerkaufMwst).where(TrainingVerkaufMwst.rechnungs_nr == v.rechnungs_nr)
    ).all()
    return {
        "rechnungs_nr": v.rechnungs_nr,
        "verkaufsdatum": v.verkaufsdatum,
        "storno_von": v.storno_von,
        "ec_zahlung": v.ec_zahlung,
        "kunde_gibt": v.kunde_gibt,
        "verkauf_details": [
            {
                "vd_id": d.vd_id,
                "rechnungs_nr": d.rechnungs_nr,
                "position": d.position,
                "artikel_id": d.artikel_id,
                "rabatt_id": d.rabatt_id,
                "stueckzahl": d.stueckzahl,
                "ges_preis": d.ges_preis,
                "mwst_satz": d.mwst_satz,
            }
            for d in details
        ],
        "verkauf_mwst": [
            {
                "rechnungs_nr": m.rechnungs_nr,
                "mwst_satz": m.mwst_satz,
                "mwst_netto": m.mwst_netto,
                "mwst_betrag": m.mwst_betrag,
            }
            for m in mwsts
        ],
    }


@router.get("/status")
def training_status() -> dict:
    return {"training_mode": is_training_mode()}


@router.get("/verkauf")
def read_training_verkaeufe(
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> list[dict]:
    rows = session.exec(
        select(TrainingVerkauf)
        .offset(offset).limit(limit)
        .order_by(TrainingVerkauf.verkaufsdatum)
    ).all()
    return [_sale_dict(v, session) for v in rows]


@router.get("/verkauf/{rechnungs_nr}")
def read_single_training_verkauf(rechnungs_nr: int, session: SessionDep) -> dict:
    v = session.get(TrainingVerkauf, rechnungs_nr)
    if not v:
        raise HTTPException(status_code=404, detail="TrainingVerkauf not found")
    return _sale_dict(v, session)


@router.post("/verkauf")
def create_training_verkauf(
    payload: Optional[TrainingVerkaufCreate],
    session: SessionDep,
    _user=Depends(require_user),
) -> dict:
    p = payload or TrainingVerkaufCreate()
    for d in (p.verkauf_details or []):
        validate_detail(session, d)

    new_v = TrainingVerkauf(
        verkaufsdatum=datetime.now(timezone.utc),
        storno_von=None,
        ec_zahlung=p.ec_zahlung,
        kunde_gibt=p.kunde_gibt,
    )
    new_v.rechnungs_nr = None
    session.add(new_v)
    session.commit()
    session.refresh(new_v)

    prepared = []
    for position, d in enumerate(p.verkauf_details or [], 1):
        vd = prepare_detail(session, d)
        row = TrainingVerkaufDetails(
            rechnungs_nr=new_v.rechnungs_nr,
            position=vd.position if vd.position is not None else position,
            artikel_id=vd.artikel_id,
            rabatt_id=vd.rabatt_id,
            stueckzahl=vd.stueckzahl,
            ges_preis=vd.ges_preis,
            mwst_satz=vd.mwst_satz,
        )
        row.vd_id = None
        session.add(row)
        prepared.append(vd)
    session.commit()

    for rate, vals in calculate_mwst_summary(prepared).items():
        session.add(TrainingVerkaufMwst(
            rechnungs_nr=new_v.rechnungs_nr,
            mwst_satz=float(rate),
            mwst_netto=float(vals["mwst_netto"]),
            mwst_betrag=float(vals["mwst_betrag"]),
        ))
    session.commit()

    # Cash training sales update the training cash balance only (mirrors
    # Kassieren.insertIntoKassenstand, which uses tableForMode("kassenstand")).
    if not p.ec_zahlung:
        last_ks = session.exec(
            select(TrainingKassenstand).order_by(TrainingKassenstand.kassenstand_id.desc())
        ).first()
        current = last_ks.neuer_kassenstand if last_ks else 0.0
        total = sum((d.ges_preis or 0.0) for d in prepared)
        ks = TrainingKassenstand(
            buchungsdatum=new_v.verkaufsdatum,
            neuer_kassenstand=round(current + total, 2),
            manuell=False,
            entnahme=False,
            rechnungs_nr=new_v.rechnungs_nr,
            kommentar="Training",
        )
        ks.kassenstand_id = None
        session.add(ks)
        session.commit()

    session.refresh(new_v)
    return _sale_dict(new_v, session)


# Aliases
read_training_verkauf = read_training_verkaeufe
create_training_sale = create_training_verkauf
