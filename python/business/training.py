"""Training sandbox: separate database with a short POS test catalog.

The Java POS only redirects the cashier tables to `training_*` tables, so
editing articles or discount actions in its training mode changes production
master data. The API instead runs the whole instance against a disposable
training database (`TRAINING_MODE` + `TRAINING_DB_URL`): every table exists
there, so all transactions *and* master-data edits are sandboxed.

On startup (and on `POST /training/reset`) the sandbox is created from the
SQLModel metadata, the production users are mirrored so authentication and the
`user_id` foreign keys work, and a short catalog is seeded that covers the POS
test cases: 0/7/19 % VAT, fixed and variable prices, deposit articles, the
special discount/voucher/deposit articles and an active discount action.
"""
from __future__ import annotations

import logging
import warnings
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SAWarning
from sqlmodel import Session, SQLModel, select

from ..models import (
    Artikel,
    Lieferant,
    Mwst,
    Pfand,
    Produktgruppe,
    Rabattaktion,
    User,
)
from ..session import get_engine, get_production_engine, is_training_mode

logger = logging.getLogger(__name__)

# `artikel_nr` of the special articles the sale workflow expects
# (`business/sale_workflow.py: SPECIAL_ARTIKEL` plus the voucher purchase).
SPECIAL_ARTIKEL = {
    "RABATT1": "Manueller Rabatt",
    "RABATT2": "Rabatt auf Rechnung",
    "ANPASSUNG": "Manuelle Preisanpassung",
    "ANZAHLUNG": "Anzahlung",
    "ANZAHLAUFLOES": "Anzahlungsauflösung",
    "GUTSCHEIN": "Gutschein",
    "GUTSCHEINEINLOES": "Gutscheineinlösung",
}

# Test articles of the seeded catalog (artikel_nr -> (name, price, variable, group))
TEST_ARTIKEL = {
    "T-19": ("Testartikel 19 % MwSt", 10.00, False, "19"),
    "T-7": ("Testartikel 7 % MwSt", 5.00, False, "7"),
    "T-0": ("Testartikel 0 % MwSt", 2.00, False, "0"),
    "T-VAR": ("Testartikel variabler Preis", None, True, "19"),
    "T-PFAND": ("Testartikel mit Pfand", 6.00, False, "pfand"),
    "T-AKTION": ("Testartikel mit Rabattaktion", 12.00, False, "19"),
    "PFAND": ("Pfand 2,00 €", 2.00, False, "pfand"),
}


def seed_catalog(session: Session) -> None:
    """Create the short training catalog if the sandbox has no articles yet."""
    if session.exec(select(Artikel)).first() is not None:
        return

    vat = {}
    for rate, key, description in (
        (0.0, 6, "Umsatzsteuerfrei"),
        (0.07, 2, "Ermäßigter Steuersatz 7 %"),
        (0.19, 1, "Allgemeiner Steuersatz 19 %"),
    ):
        row = Mwst(
            mwst_satz=rate,
            dsfinvk_ust_schluessel=key,
            dsfinvk_ust_beschr=description,
        )
        session.add(row)
        session.flush()
        vat[rate] = row

    supplier = Lieferant(lieferant_name="Trainingslieferant", lieferant_kurzname="Training")
    session.add(supplier)
    session.flush()

    groups = {}
    for key, name, mwst, pfand_id in (
        ("rabatt", "Rabatt", None, None),
        ("gutschein", "Gutschein", vat[0.0], None),
        ("pfand", "Pfand", vat[0.19], None),
        ("19", "Testware 19 %", vat[0.19], None),
        ("7", "Testware 7 %", vat[0.07], None),
        ("0", "Testware 0 %", vat[0.0], None),
        ("mit_pfand", "Testware mit Pfand", vat[0.19], None),
    ):
        row = Produktgruppe(
            produktgruppen_name=name,
            toplevel_id=1,
            mwst_id=mwst.mwst_id if mwst is not None else None,
        )
        session.add(row)
        session.flush()
        groups[key] = row

    def artikel(nr: str, name: str, group: Produktgruppe, price=None, variable=False) -> Artikel:
        row = Artikel(
            artikel_nr=nr,
            artikel_name=name,
            kurzname=name[:50],
            produktgruppen_id=group.produktgruppen_id,
            lieferant_id=supplier.lieferant_id,
            vk_preis=price,
            variabler_preis=variable,
            sortiment=not nr.startswith(("RABATT", "ANPASSUNG", "ANZAHLUNG", "GUTSCHEIN")),
            aktiv=True,
        )
        session.add(row)
        session.flush()
        return row

    for nr, name in SPECIAL_ARTIKEL.items():
        group = groups["gutschein"] if nr.startswith("GUTSCHEIN") else groups["rabatt"]
        artikel(nr, name, group, variable=True)

    # The deposit article must exist before the Pfand row and the group that
    # uses it; sale positions of that group then get the deposit added.
    pfand_artikel = artikel("PFAND", TEST_ARTIKEL["PFAND"][0], groups["pfand"], 2.00)
    pfand = Pfand(artikel_id=pfand_artikel.artikel_id)
    session.add(pfand)
    session.flush()
    groups["pfand"].pfand_id = pfand.pfand_id
    groups["mit_pfand"].pfand_id = pfand.pfand_id
    session.add(groups["pfand"])
    session.add(groups["mit_pfand"])

    articles = {}
    for nr, (name, price, variable, group) in TEST_ARTIKEL.items():
        if nr == "PFAND":
            articles[nr] = pfand_artikel
            continue
        articles[nr] = artikel(nr, name, groups[group], price, variable)

    session.add(Rabattaktion(
        aktionsname="Trainingsaktion 10 %",
        artikel_id=articles["T-AKTION"].artikel_id,
        rabatt_relativ=0.10,
        von=datetime.now(timezone.utc) - timedelta(days=1),
        bis=None,
    ))
    session.commit()
    logger.info("Training catalog seeded")


def mirror_users(session: Session, production_engine: Engine) -> None:
    """Copy production users into the sandbox (auth and `user_id` foreign keys)."""
    with Session(production_engine) as source:
        users = source.exec(select(User)).all()
    for user in users:
        target = session.get(User, user.user_id)
        if target is None:
            session.add(User(
                user_id=user.user_id,
                username=user.username,
                password_hash=user.password_hash,
                role=user.role,
                active=user.active,
            ))
        else:
            target.username = user.username
            target.password_hash = user.password_hash
            target.role = user.role
            target.active = user.active
    session.commit()


def ensure_training_database() -> None:
    """Create and seed the sandbox when this instance runs in training mode."""
    if not is_training_mode():
        return
    engine = get_engine()
    production = get_production_engine()
    if engine is production or (
        not str(engine.url).startswith("sqlite") and engine.url == production.url
    ):
        raise RuntimeError("TRAINING_DB_URL must not point to the production database")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        mirror_users(session, production)
        seed_catalog(session)


def reset_training_data(session: Session, production_engine: Engine | None = None) -> None:
    """Clear all sandbox data (users keep) and seed the catalog again."""
    catalog_tables = {"artikel", "pfand", "produktgruppe", "rabattaktion", "lieferant", "mwst"}
    # `artikel`/`pfand`/`produktgruppe` form a foreign-key cycle, so the catalog
    # is deleted in an explicit order below; `sorted_tables` only orders the
    # transaction tables (the cycle warning is expected and harmless here).
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SAWarning)
        tables = list(reversed(SQLModel.metadata.sorted_tables))
    for table in tables:
        if table.name in ("user", "anmeldung") or table.name in catalog_tables:
            continue
        session.execute(delete(table))
    session.execute(update(Produktgruppe).values(pfand_id=None))
    session.execute(delete(Pfand.__table__))
    session.execute(delete(Rabattaktion.__table__))
    session.execute(delete(Artikel.__table__))
    session.execute(delete(Produktgruppe.__table__))
    session.execute(delete(Lieferant.__table__))
    session.execute(delete(Mwst.__table__))
    session.commit()
    if production_engine is not None:
        mirror_users(session, production_engine)
    seed_catalog(session)


__all__ = [
    "SPECIAL_ARTIKEL",
    "TEST_ARTIKEL",
    "ensure_training_database",
    "mirror_users",
    "reset_training_data",
    "seed_catalog",
]
