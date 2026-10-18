from datetime import datetime, timezone, date
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from ..models import (
    AbrechnungTag,
    AbrechnungTagPublic,
    AbrechnungTagCreate,
    AbrechnungTagMwst,
    AbrechnungTagMwstPublic,
    Kassenstand,
    KassenstandCreate,
    Verkauf,
    VerkaufMwst,
)
from ..session import SessionDep

router = APIRouter(
    prefix="/abrechnung/tag",
    tags=["abrechnung_tag"],
    responses={404: {"description": "Not found"}},
)


def _last_tag(session: SessionDep):
    return session.exec(select(AbrechnungTag).order_by(AbrechnungTag.id.desc())).first()


@router.get("/")
def read_abrechnung_tags(
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> list[AbrechnungTagPublic]:
    rows = session.exec(
        select(AbrechnungTag).offset(offset).limit(limit).order_by(AbrechnungTag.id)
    ).all()
    return [AbrechnungTagPublic.model_validate(r) for r in rows]


@router.get("/offen")
def read_offene_abrechnung_tags(session: SessionDep) -> list[str]:
    last = _last_tag(session)
    last_bis = last.rechnungs_nr_bis if last else 0
    sales = session.exec(
        select(Verkauf).where(Verkauf.rechnungs_nr > last_bis).order_by(Verkauf.verkaufsdatum)
    ).all()
    dates = []
    seen = set()
    for s in sales:
        d = s.verkaufsdatum.date().isoformat()
        if d not in seen:
            seen.add(d)
            dates.append(d)
    return dates


@router.get("/{tag_id}")
def read_single_abrechnung_tag(tag_id: int, session: SessionDep) -> dict:
    t = session.get(AbrechnungTag, tag_id)
    if not t:
        raise HTTPException(status_code=404, detail="AbrechnungTag not found")
    mwsts = session.exec(
        select(AbrechnungTagMwst).where(AbrechnungTagMwst.id == tag_id)
    ).all()
    obj = AbrechnungTagPublic.model_validate(t).model_dump()
    obj["mwst"] = [AbrechnungTagMwstPublic.model_validate(m).model_dump() for m in mwsts]
    return obj


@router.post("/", response_model=AbrechnungTagPublic)
def create_abrechnung_tag(payload: Optional[AbrechnungTagCreate], session: SessionDep):
    p = payload or AbrechnungTagCreate()
    now = datetime.now(timezone.utc)

    # Determine rechnungs range
    if p.rechnungs_nr_von is not None and p.rechnungs_nr_bis is not None:
        von = p.rechnungs_nr_von
        bis = p.rechnungs_nr_bis
    else:
        last = _last_tag(session)
        last_bis = last.rechnungs_nr_bis if last else 0
        first_sale = session.exec(
            select(Verkauf).where(Verkauf.rechnungs_nr > last_bis).order_by(Verkauf.rechnungs_nr)
        ).first()
        if not first_sale:
            raise HTTPException(status_code=400, detail="No sales to settle")
        last_sale = session.exec(
            select(Verkauf).where(Verkauf.rechnungs_nr > last_bis).order_by(Verkauf.rechnungs_nr.desc())
        ).first()
        von = first_sale.rechnungs_nr
        bis = last_sale.rechnungs_nr

    sales = session.exec(
        select(Verkauf).where(Verkauf.rechnungs_nr >= von, Verkauf.rechnungs_nr <= bis)
    ).all()
    if not sales:
        raise HTTPException(status_code=400, detail="No sales in range")

    # Aggregate VAT
    mwst_map = {}
    for v in sales:
        for m in v.verkauf_mwst or []:
            entry = mwst_map.setdefault(m.mwst_satz, {"netto": 0.0, "betrag": 0.0, "bar": 0.0})
            entry["netto"] += m.mwst_netto
            entry["betrag"] += m.mwst_betrag
    for v in sales:
        if v.ec_zahlung:
            continue
        for d in v.verkauf_details or []:
            if d.mwst_satz is None:
                continue
            entry = mwst_map.setdefault(d.mwst_satz, {"netto": 0.0, "betrag": 0.0, "bar": 0.0})
            entry["bar"] += d.ges_preis

    # Create kassenstand (Tagesabschluss entry) if not provided
    ks_id = p.kassenstand_id
    if ks_id is None:
        current_balance = 0.0
        last_ks = session.exec(select(Kassenstand).order_by(Kassenstand.kassenstand_id.desc())).first()
        if last_ks:
            current_balance = last_ks.neuer_kassenstand
        total_bar = sum(e["bar"] for e in mwst_map.values())
        new_ks = Kassenstand(
            buchungsdatum=now,
            neuer_kassenstand=current_balance + total_bar,
            manuell=True,
            entnahme=False,
            kommentar="Tagesabschluss",
        )
        new_ks.kassenstand_id = None
        session.add(new_ks)
        session.commit()
        session.refresh(new_ks)
        ks_id = new_ks.kassenstand_id

    at = AbrechnungTag(
        z_kasse_id=p.z_kasse_id or "1",
        zeitpunkt=p.zeitpunkt or now,
        zeitpunkt_real=p.zeitpunkt_real or now,
        kassenstand_id=ks_id,
        rechnungs_nr_von=von,
        rechnungs_nr_bis=bis,
        last_tse_sig_counter=p.last_tse_sig_counter,
    )
    at.id = None
    session.add(at)
    session.commit()
    session.refresh(at)

    for satz, vals in mwst_map.items():
        row = AbrechnungTagMwst(
            id=at.id,
            mwst_satz=satz,
            mwst_netto=vals["netto"],
            mwst_betrag=vals["betrag"],
            bar_brutto=vals["bar"],
        )
        session.add(row)
    session.commit()

    return AbrechnungTagPublic.model_validate(at)


# Aliases
read_abrechnung_tag = read_abrechnung_tags
read_abrechnung_tags_alias = read_abrechnung_tags
create_abrechnung_tag_entry = create_abrechnung_tag