"""Stateless cart helpers.

The cart itself lives in the GUI, but all price, VAT, Pfand and discount rules
stay here: every endpoint takes the current cart context and returns the rows
the client must display (or send back for the sale). This shares the expansion
with `POST /verkauf`, so a preview cannot diverge from the final receipt.
"""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from fastapi import APIRouter

from ..business.errors import DomainError
from ..business.sale_workflow import (
    expand_details,
    receipt_discount_rows,
    calculate_mwst_summary,
)
from ..models import Artikel, VerkaufDetails
from ..schemas import (
    VerkaufDetailsCreate,
    WarenkorbHinzufuegen,
    WarenkorbPosition,
    WarenkorbLeergut,
    WarenkorbRabatt,
    WarenkorbSummenAnfrage,
    WarenkorbSummen,
    WarenkorbMwst,
)
from ..session import SessionDep

router = APIRouter(prefix="/warenkorb", tags=["warenkorb"])

CENT = Decimal("0.01")

SPECIAL_KINDS = {
    "RABATT1": "rabatt",
    "RABATT2": "rechnung_rabatt",
    "ANPASSUNG": "preisanpassung",
    "ANZAHLUNG": "anzahlung",
    "ANZAHLAUFLOES": "anzahlungsaufloesung",
    "GUTSCHEINEINLOES": "gutschein",
}


def _position(session: SessionDep, detail, ref, parent_ref=None, kind="artikel",
              rabatt_absolut=None, hat_rabatt=False) -> WarenkorbPosition:
    artikel = session.get(Artikel, detail.artikel_id) if detail.artikel_id else None
    stueckzahl = detail.stueckzahl or 1
    row_kind = SPECIAL_KINDS.get(artikel.artikel_nr, kind) if artikel else kind
    lieferant = artikel.lieferant if artikel is not None else None
    unit = (Decimal(str(detail.ges_preis)) / Decimal(stueckzahl)).quantize(
        CENT, rounding=ROUND_HALF_UP)
    return WarenkorbPosition(
        ref=ref,
        parent_ref=parent_ref,
        kind=row_kind,
        artikel_id=detail.artikel_id,
        artikel_name=artikel.artikel_name if artikel is not None else "",
        kurzname=artikel.kurzname if artikel is not None else None,
        lieferant_kurzname=lieferant.lieferant_kurzname if lieferant is not None else None,
        artikel_nr=artikel.artikel_nr if artikel is not None else "",
        stueckzahl=stueckzahl,
        einzelpreis=float(unit),
        ges_preis=float(detail.ges_preis),
        mwst_satz=float(detail.mwst_satz),
        variabler_preis=bool(artikel.variabler_preis) if artikel is not None else False,
        rabatt_id=detail.rabatt_id,
        rabatt_absolut=rabatt_absolut,
        hat_rabatt=hat_rabatt,
    )


def _expand_one(session, artikel_id, stueckzahl, preis, ref):
    detail = VerkaufDetailsCreate(
        artikel_id=artikel_id, stueckzahl=stueckzahl, ges_preis=preis)
    rows, _ = expand_details(session, [detail])
    if not rows:
        raise DomainError(detail="Artikel could not be added")
    positions = [_position(session, rows[0], ref)]
    pfand_ids = {
        artikel.produktgruppe.pfand.artikel_id
        for artikel in [session.get(Artikel, artikel_id)]
        if artikel is not None and artikel.produktgruppe is not None
        and artikel.produktgruppe.pfand is not None
    }
    for index, row in enumerate(rows[1:], start=1):
        kind = "pfand" if row.artikel_id in pfand_ids else "rabatt"
        positions.append(_position(
            session, row, f"{ref}-{kind}-{index}", parent_ref=ref, kind=kind))
    return positions


@router.post("/hinzufuegen", response_model=list[WarenkorbPosition])
def hinzufuegen(payload: WarenkorbHinzufuegen, session: SessionDep):
    """Add an article to the cart.

    Returns the article row plus the rows it requires: its product-group Pfand
    and any active Rabattaktion. A variable-price article keeps `preis` (the
    line total); without it the line is 0 until a price is entered.
    """
    artikel = session.get(Artikel, payload.artikel_id)
    if artikel is None:
        raise DomainError(detail="Artikel not found")
    ref = payload.ref or f"artikel-{payload.artikel_id}"
    return _expand_one(session, payload.artikel_id, payload.stueckzahl, payload.preis, ref)


@router.post("/leergut", response_model=list[WarenkorbPosition])
def leergut(payload: WarenkorbLeergut, session: SessionDep):
    """Return the Pfand row of the given article with a negative price.

    Used when a customer returns empty bottles: the article itself is not put
    into the cart, only its deposit.
    """
    artikel = session.get(Artikel, payload.artikel_id)
    if artikel is None:
        raise DomainError(detail="Artikel not found")
    pfand = artikel.produktgruppe.pfand if artikel.produktgruppe is not None else None
    if pfand is None or pfand.artikel is None or pfand.artikel.vk_preis is None:
        raise DomainError(detail=f"No Pfand configured for {artikel.artikel_name}")
    pfand_artikel = pfand.artikel
    pg = pfand_artikel.produktgruppe
    mwst_satz = float(pg.mwst.mwst_satz) if pg is not None and pg.mwst is not None else 0.0
    total = (Decimal(str(pfand_artikel.vk_preis)) * Decimal(payload.stueckzahl)).quantize(
        CENT, rounding=ROUND_HALF_UP)
    detail = VerkaufDetails(
        position=None,
        artikel_id=pfand_artikel.artikel_id,
        stueckzahl=payload.stueckzahl,
        ges_preis=float(-total),
        mwst_satz=mwst_satz,
        rabatt_id=None,
    )
    row_ref = payload.ref or f"leergut-{pfand_artikel.artikel_id}"
    return [_position(session, detail, row_ref, kind="leergut")]


def _line_total(session, item) -> Decimal:
    if item.ges_preis is not None:
        return Decimal(str(item.ges_preis))
    artikel = session.get(Artikel, item.artikel_id)
    if artikel is None:
        raise DomainError(detail="Artikel not found")
    if artikel.variabler_preis or artikel.vk_preis is None:
        raise DomainError(detail="Variable-price article requires ges_preis")
    return (Decimal(str(artikel.vk_preis)) * Decimal(item.stueckzahl)).quantize(
        CENT, rounding=ROUND_HALF_UP)


@router.post("/rabatt", response_model=list[WarenkorbPosition])
def rabatt(payload: WarenkorbRabatt, session: SessionDep):
    """Apply a discount and return the rows to display.

    Per article: returns the echoed article row (with `rabatt_absolut` for the
    sale payload) followed by its negative Rabatt rows. With `rechnung=true`
    the discount applies to the whole receipt and returns one negative row per
    VAT rate, skipping articles that already carry a discount.
    """
    if payload.rabatt.art == "relativ" and not 0 < payload.rabatt.wert < 1:
        raise DomainError(detail="Relative discount must be between 0 and 1")

    if payload.rechnung:
        if payload.rabatt.art != "relativ":
            raise DomainError(detail="Receipt discount is relative")
        details = [
            VerkaufDetailsCreate(
                artikel_id=item.artikel_id,
                stueckzahl=item.stueckzahl,
                ges_preis=item.ges_preis,
                rabatt_id=item.rabatt_id,
            )
            for item in payload.positionen
        ]
        _, article_rows = expand_details(session, details)
        rows = receipt_discount_rows(
            session, article_rows, Decimal(str(payload.rabatt.wert)))
        return [
            _position(session, row, f"rechnung-rabatt-{index}", kind="rechnung_rabatt")
            for index, row in enumerate(rows, start=1)
        ]

    positions: list[WarenkorbPosition] = []
    for item in payload.positionen:
        total = _line_total(session, item)
        if total <= 0:
            raise DomainError(detail="Rabatt requires a positive line price")
        amount = (
            Decimal(str(payload.rabatt.wert)) * total
            if payload.rabatt.art == "relativ"
            else Decimal(str(payload.rabatt.wert))
        ).quantize(CENT, rounding=ROUND_HALF_UP)
        if amount <= 0:
            raise DomainError(detail="Rabatt amount is zero")
        if amount > total:
            raise DomainError(detail="Rabatt exceeds the line price")
        try:
            per_unit = (amount / Decimal(item.stueckzahl)).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP)
        except InvalidOperation:
            raise DomainError(detail="Invalid discount amount")

        detail = VerkaufDetailsCreate(
            artikel_id=item.artikel_id,
            stueckzahl=item.stueckzahl,
            ges_preis=float(total),
            rabatt_id=item.rabatt_id,
            rabatt_absolut=float(per_unit),
        )
        rows, _ = expand_details(session, [detail])
        echoed = _position(
            session, rows[0], item.ref, kind="artikel",
            rabatt_absolut=float(per_unit), hat_rabatt=True)
        positions.append(echoed)
        for index, row in enumerate(rows[1:], start=1):
            kind = "pfand" if row.artikel_id != item.artikel_id and row.rabatt_id is None else "rabatt"
            positions.append(_position(
                session, row, f"{item.ref}-{kind}-{index}",
                parent_ref=item.ref, kind=kind))
    return positions


@router.post("/summen", response_model=WarenkorbSummen)
def summen(payload: WarenkorbSummenAnfrage, session: SessionDep):
    """Totals of the current cart rows (subtotal, VAT split, discounts, change)."""
    rows = payload.positionen
    discount_kinds = {"rabatt", "rechnung_rabatt"}
    zwischensumme = sum(
        (Decimal(str(row.ges_preis)) for row in rows if row.kind not in discount_kinds),
        Decimal("0"),
    )
    rabatte = -sum(
        (Decimal(str(row.ges_preis)) for row in rows if row.kind in discount_kinds),
        Decimal("0"),
    )
    zu_zahlen = sum((Decimal(str(row.ges_preis)) for row in rows), Decimal("0"))
    summary = calculate_mwst_summary(rows)
    rueckgeld = None
    if payload.kunde_gibt is not None:
        rueckgeld = float(Decimal(str(payload.kunde_gibt)) - zu_zahlen)
    return WarenkorbSummen(
        zwischensumme=float(zwischensumme),
        rabatte=float(rabatte),
        zu_zahlen=float(zu_zahlen),
        mwst=[
            WarenkorbMwst(
                mwst_satz=float(rate),
                mwst_netto=float(values["mwst_netto"]),
                mwst_betrag=float(values["mwst_betrag"]),
                brutto=float(values["brutto"]),
            )
            for rate, values in sorted(summary.items())
        ],
        rueckgeld=rueckgeld,
    )
