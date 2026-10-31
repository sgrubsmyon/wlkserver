"""ORM table models (SQLModel `table=True`) and their column bases.

API schemas (Public/Create/Update/Details) live in `python/schemas`.
"""
from datetime import date, datetime, timezone
from typing import Literal, Optional

from sqlalchemy import DATE, DECIMAL, TIMESTAMP, Column, event
from sqlalchemy.orm import backref
from sqlmodel import Field, Relationship, SQLModel

# The base model, shared by all
class LieferantBase(SQLModel):
    lieferant_name: str = Field(max_length=50, nullable=False)
    lieferant_kurzname: str | None = Field(max_length=10)


# The table model
class Lieferant(LieferantBase, table=True):
    __tablename__ = 'lieferant'

    lieferant_id: int | None = Field(default=None, primary_key=True)
    n_artikel: int | None = Field(default=None) # sa_column_kwargs={"unsigned": True}
    aktiv: bool = Field(nullable=False, default=True)

    artikel: list["Artikel"] = Relationship(back_populates="lieferant")


# The base model, shared by all
class MwstBase(SQLModel):
    mwst_satz: float = Field(ge=0, le=1, sa_column=DECIMAL(precision=6, scale=5))
    dsfinvk_ust_schluessel: int = Field(nullable=False) # sa_column_kwargs={"unsigned": True}, 
    dsfinvk_ust_beschr: str | None = Field(max_length=55)


# The table model
class Mwst(MwstBase, table=True):
    __tablename__ = 'mwst'

    mwst_id: int | None = Field(default=None, primary_key=True)
    # mwst_satz: float = Field(sa_column= Column(DECIMAL(precision=6, scale=5), nullable=True))
    # dsfinvk_ust_schluessel: int = Field(nullable=False) # sa_column_kwargs={"unsigned": True}, 
    # dsfinvk_ust_beschr: str | None = Field(max_length=55)

    # relationships
    produktgruppe: list["Produktgruppe"] = Relationship(back_populates="mwst")


class Pfand(SQLModel, table=True):
    __tablename__ = 'pfand'

    pfand_id: int | None = Field(default=None, primary_key=True)
    artikel_id: int = Field(foreign_key="artikel.artikel_id") # sa_column_kwargs={"unsigned": True},

    artikel: "Artikel" = Relationship(back_populates="pfand")
    produktgruppe: list["Produktgruppe"] = Relationship(back_populates="pfand")


# The base model, shared by all
class ProduktgruppeBase(SQLModel):
    toplevel_id: int = Field(default=1) # sa_column_kwargs={"unsigned": True}, 
    sub_id: int | None = Field(default=None) # sa_column_kwargs={"unsigned": True}
    subsub_id: int | None = Field(default=None) # sa_column_kwargs={"unsigned": True}
    produktgruppen_name: str = Field(max_length=50, nullable=False)
    std_einheit: str | None = Field(max_length=10)


# The table model
class Produktgruppe(ProduktgruppeBase, table=True):
    __tablename__ = 'produktgruppe'

    produktgruppen_id: int | None = Field(default=None, primary_key=True)
    mwst_id: int | None = Field(default=None, foreign_key="mwst.mwst_id") # sa_column_kwargs={"unsigned": True}, 
    pfand_id: int | None = Field(default=None, foreign_key="pfand.pfand_id") # sa_column_kwargs={"unsigned": True}, 

    aktiv: bool = Field(nullable=False, default=True)
    n_artikel: int | None = Field(default=None) # sa_column_kwargs={"unsigned": True}
    n_artikel_rekursiv: int | None = Field(default=None) # sa_column_kwargs={"unsigned": True}
    
    # relationships
    mwst: Mwst = Relationship(back_populates="produktgruppe")
    pfand: Pfand | None = Relationship(back_populates="produktgruppe")
    artikel: list["Artikel"] = Relationship(back_populates="produktgruppe")
    rabattaktion: list["Rabattaktion"] = Relationship(back_populates="produktgruppe")


# The base model, shared by all
class ArtikelBase(SQLModel):
    artikel_nr: str = Field(max_length=30, nullable=False)
    artikel_name: str = Field(max_length=180, nullable=False)
    kurzname: str | None = Field(max_length=50, default=None)
    menge: float | None = Field(sa_column=DECIMAL(precision=8, scale=5), default=None, ge=0)
    einheit: str | None = Field(max_length=10, default=None)
    barcode: str | None = Field(max_length=30, default=None)
    herkunft: str | None = Field(max_length=100, default=None)
    vpe: int | None = Field(default=None) # sa_column_kwargs={"unsigned": True}
    setgroesse: int = Field(nullable=False, default=1, ge=1) # sa_column_kwargs={"unsigned": True}, 
    vk_preis: float | None = Field(sa_column=DECIMAL(precision=13, scale=2), default=None, ge=0)
    empf_vk_preis: float | None = Field(sa_column=DECIMAL(precision=13, scale=2), default=None, ge=0)
    ek_rabatt: float | None = Field(sa_column=DECIMAL(precision=6, scale=5), default=None, ge=0, le=1)
    ek_preis: float | None = Field(sa_column=DECIMAL(precision=13, scale=2), default=None, ge=0)
    variabler_preis: bool = Field(nullable=False, default=False)
    sortiment: bool = Field(nullable=False, default=False)
    lieferbar: bool = Field(nullable=False, default=False)
    beliebtheit: int = Field(nullable=False, default=0)
    bestand: int | None = Field(default=None) # sa_column_kwargs={"unsigned": True}


# The table model
class Artikel(ArtikelBase, table=True):
    __tablename__ = 'artikel'

    artikel_id: int | None = Field(default=None, primary_key=True)
    # id = Column(Integer, Sequence('user_id_seq', start=100, increment=1), primary_key=True)
    produktgruppen_id: int = Field(foreign_key="produktgruppe.produktgruppen_id", nullable=False, default=8)
    lieferant_id: int = Field(foreign_key="lieferant.lieferant_id", nullable=False, default=1)

    von: datetime | None = Field(sa_column=Column(TIMESTAMP, nullable=True), default=None)
    bis: datetime | None = Field(sa_column=Column(TIMESTAMP, nullable=True), default=None)
    aktiv: bool = Field(nullable=False, default=True)

    # relationships
    produktgruppe: "Produktgruppe" = Relationship(back_populates="artikel")
    lieferant: "Lieferant" = Relationship(back_populates="artikel")
    pfand: Pfand = Relationship(back_populates="artikel")
    rabattaktion: list["Rabattaktion"] = Relationship(back_populates="artikel")
    verkauf_details: list["VerkaufDetails"] = Relationship(back_populates="artikel")


# The base model, shared by all
class RabattaktionBase(SQLModel):
    aktionsname: str = Field(max_length=50, default=None)
    rabatt_relativ: float | None = Field(sa_column=DECIMAL(precision=6, scale=5), default=None, ge=0, le=1)
    rabatt_absolut: float | None = Field(sa_column=DECIMAL(precision=13, scale=2), default=None, ge=0)
    mengenrabatt_schwelle: int | None = Field(default=None, ge=1) # sa_column_kwargs={"unsigned": True}
    mengenrabatt_anzahl_kostenlos: int | None = Field(default=None, ge=1) # sa_column_kwargs={"unsigned": True}
    mengenrabatt_relativ: float | None = Field(sa_column=DECIMAL(precision=6, scale=5), default=None, ge=0, le=1)
    von: datetime = Field(sa_column=Column(TIMESTAMP, nullable=False))
    bis: datetime | None = Field(sa_column=Column(TIMESTAMP, nullable=True), default=None)


# The table model
class Rabattaktion(RabattaktionBase, table=True):
    __tablename__ = 'rabattaktion'

    rabatt_id: int | None = Field(default=None, primary_key=True)

    produktgruppen_id: int | None = Field(default=None, foreign_key="produktgruppe.produktgruppen_id") # sa_column_kwargs={"unsigned": True},
    artikel_id: int | None = Field(default=None, foreign_key="artikel.artikel_id") # sa_column_kwargs={"unsigned": True},

    # relationships
    produktgruppe: "Produktgruppe" = Relationship(back_populates="rabattaktion")
    artikel: "Artikel" = Relationship(back_populates="rabattaktion")
    verkauf_details: list["VerkaufDetails"] = Relationship(back_populates="rabattaktion")


# The base model, shared by all
class VerkaufBase(SQLModel):
    ec_zahlung: bool = Field(nullable=False, default=False)
    kunde_gibt: float | None = Field(sa_column=DECIMAL(precision=13, scale=2), default=None, ge=0)
    user_id: int | None = Field(default=None, foreign_key="user.user_id")


# The table model
class Verkauf(VerkaufBase, table=True):
    __tablename__ = 'verkauf'

    verkaufsdatum: datetime = Field(sa_column=Column(TIMESTAMP, nullable=False))

    # primary key
    rechnungs_nr: int | None = Field(default=None, primary_key=True)

    # foreign keys
    storno_von: int | None = Field(default=None, foreign_key="verkauf.rechnungs_nr") # sa_column_kwargs={"unsigned": True},

    # relationships
    # Self-referential relationships (original <-> storno)
    # See https://github.com/fastapi/sqlmodel/issues/127 for backref usage and self-referential relationships in SQLModel
    stornierter_verkauf: Optional["Verkauf"] = Relationship(
        back_populates="stornierender_verkauf",
        sa_relationship_kwargs=dict(
            remote_side="Verkauf.rechnungs_nr"
        )
    )
    stornierender_verkauf: Optional["Verkauf"] = Relationship(back_populates="stornierter_verkauf")

    verkauf_mwst: list["VerkaufMwst"] = Relationship(back_populates="verkauf")
    verkauf_details: list["VerkaufDetails"] = Relationship(back_populates="verkauf")


# The base model, shared by all
class VerkaufMwstBase(SQLModel):
    mwst_netto: float = Field(sa_column=DECIMAL(precision=13, scale=2))
    mwst_betrag: float = Field(sa_column=DECIMAL(precision=13, scale=2))


# The table model
class VerkaufMwst(VerkaufMwstBase, table=True):
    __tablename__ = 'verkauf_mwst'

    # primary key
    rechnungs_nr: int = Field(nullable=False, primary_key=True, foreign_key="verkauf.rechnungs_nr")
    mwst_satz: float = Field(nullable=False, primary_key=True) # sa_column=DECIMAL(precision=6, scale=5), 

    # relationships
    verkauf: "Verkauf" = Relationship(back_populates="verkauf_mwst")


# The base model, shared by all
class VerkaufDetailsBase(SQLModel):
    position: int | None = Field(default=None) # , sa_column_kwargs={"unsigned": True}
    stueckzahl: int = Field(nullable=False, default=1) # sa_column_kwargs={"unsigned": True},


# The table model
class VerkaufDetails(VerkaufDetailsBase, table=True):
    __tablename__ = 'verkauf_details'

    # primary key
    vd_id: int | None = Field(default=None, primary_key=True)

    ges_preis: float = Field(sa_column=DECIMAL(precision=13, scale=2))
    mwst_satz: float = Field(sa_column=DECIMAL(precision=6, scale=5))
    
    # foreign keys
    rechnungs_nr: int = Field(nullable=False, foreign_key="verkauf.rechnungs_nr") # sa_column_kwargs={"unsigned": True},
    artikel_id: int | None = Field(default=None, foreign_key="artikel.artikel_id") # sa_column_kwargs={"unsigned": True},
    rabatt_id: int | None = Field(default=None, foreign_key="rabattaktion.rabatt_id") # sa_column_kwargs={"unsigned": True},

    # relationships
    verkauf: "Verkauf" = Relationship(back_populates="verkauf_details")
    artikel: "Artikel" = Relationship(back_populates="verkauf_details")
    rabattaktion: "Rabattaktion" = Relationship(back_populates="verkauf_details")


class Kassenstand(SQLModel, table=True):
    __tablename__ = "kassenstand"

    kassenstand_id: int | None = Field(default=None, primary_key=True)
    buchungsdatum: datetime = Field(sa_column=Column(TIMESTAMP, nullable=False))
    neuer_kassenstand: float = Field(ge=0, sa_column=DECIMAL(precision=13, scale=2))
    manuell: bool = Field(nullable=False, default=False)
    entnahme: bool = Field(nullable=False, default=False)
    rechnungs_nr: int | None = Field(default=None, foreign_key="verkauf.rechnungs_nr")
    kommentar: str | None = Field(max_length=70, default=None)
    user_id: int | None = Field(default=None, foreign_key="user.user_id")


class GutscheinCounter(SQLModel, table=True):
    """Highest assigned voucher number (single row, id=1).

    Voucher creation locks this row with `SELECT ... FOR UPDATE`, so concurrent
    cash registers cannot pick the same `gutschein_nr`.
    """
    __tablename__ = "gutschein_counter"

    id: int = Field(default=1, primary_key=True)
    last_nr: int = Field(nullable=False)


class Gutschein(SQLModel, table=True):
    __tablename__ = "gutschein"

    gutschein_id: int | None = Field(default=None, primary_key=True)
    gutschein_nr: int = Field(nullable=False)
    datum: datetime = Field(sa_column=Column(TIMESTAMP, nullable=False))
    gutschein_in_vd_id: int | None = Field(default=None, foreign_key="verkauf_details.vd_id")
    einloesung_in_vd_id: int | None = Field(default=None, foreign_key="verkauf_details.vd_id")
    restbetrag: float = Field(ge=0, sa_column=DECIMAL(precision=13, scale=2))
    user_id: int | None = Field(default=None, foreign_key="user.user_id")


class Anzahlung(SQLModel, table=True):
    __tablename__ = "anzahlung"

    anzahlung_id: int | None = Field(default=None, primary_key=True)
    datum: datetime = Field(sa_column=Column(TIMESTAMP, nullable=False))
    anzahlung_in_rech_nr: int = Field(foreign_key="verkauf.rechnungs_nr", nullable=False)
    aufloesung_in_rech_nr: int | None = Field(default=None, foreign_key="verkauf.rechnungs_nr")
    user_id: int | None = Field(default=None, foreign_key="user.user_id")


class AnzahlungDetails(SQLModel, table=True):
    __tablename__ = "anzahlung_details"

    ad_id: int | None = Field(default=None, primary_key=True)
    rechnungs_nr: int = Field(foreign_key="verkauf.rechnungs_nr", nullable=False)
    vd_id: int = Field(foreign_key="verkauf_details.vd_id", nullable=False)
    ges_preis: float = Field(sa_column=DECIMAL(precision=13, scale=2))


class AbrechnungTag(SQLModel, table=True):
    __tablename__ = "abrechnung_tag"

    id: int | None = Field(default=None, primary_key=True)
    z_kasse_id: str = Field(max_length=30, nullable=False, default="1")
    zeitpunkt: datetime = Field(sa_column=Column(TIMESTAMP, nullable=False))
    zeitpunkt_real: datetime = Field(sa_column=Column(TIMESTAMP, nullable=False))
    kassenstand_id: int | None = Field(default=None, foreign_key="kassenstand.kassenstand_id")
    user_id: int | None = Field(default=None, foreign_key="user.user_id")
    rechnungs_nr_von: int = Field(foreign_key="verkauf.rechnungs_nr", nullable=False)
    rechnungs_nr_bis: int = Field(foreign_key="verkauf.rechnungs_nr", nullable=False)
    last_tse_sig_counter: int | None = Field(default=None)


class AbrechnungTagMwst(SQLModel, table=True):
    __tablename__ = "abrechnung_tag_mwst"

    id: int = Field(primary_key=True, foreign_key="abrechnung_tag.id")
    mwst_satz: float = Field(sa_column=Column(DECIMAL(precision=6, scale=5), primary_key=True, nullable=False))
    mwst_netto: float = Field(sa_column=DECIMAL(precision=13, scale=2))
    mwst_betrag: float = Field(sa_column=DECIMAL(precision=13, scale=2))
    bar_brutto: float = Field(sa_column=DECIMAL(precision=13, scale=2))


class AbrechnungTagTse(SQLModel, table=True):
    __tablename__ = "abrechnung_tag_tse"

    id: int = Field(primary_key=True, foreign_key="abrechnung_tag.id")
    tse_id: int | None = None
    tse_serial: str | None = Field(max_length=68, default=None)
    tse_sig_algo: str | None = Field(max_length=21, default=None)
    tse_time_format: str | None = Field(max_length=31, default=None)
    tse_pd_encoding: str | None = Field(max_length=5, default=None)
    tse_public_key: str | None = Field(max_length=512, default=None)
    tse_cert_i: str | None = Field(max_length=1000, default=None)
    tse_cert_ii: str | None = Field(max_length=1000, default=None)


class AbrechnungMonat(SQLModel, table=True):
    __tablename__ = "abrechnung_monat"

    id: int | None = Field(default=None, primary_key=True)
    monat: date = Field(sa_column=Column(DATE, nullable=False))
    abrechnung_tag_id_von: int = Field(foreign_key="abrechnung_tag.id", nullable=False)
    abrechnung_tag_id_bis: int = Field(foreign_key="abrechnung_tag.id", nullable=False)


class AbrechnungMonatMwst(SQLModel, table=True):
    __tablename__ = "abrechnung_monat_mwst"

    id: int = Field(primary_key=True, foreign_key="abrechnung_monat.id")
    mwst_satz: float = Field(sa_column=Column(DECIMAL(precision=6, scale=5), primary_key=True, nullable=False))
    mwst_netto: float = Field(sa_column=DECIMAL(precision=13, scale=2))
    mwst_betrag: float = Field(sa_column=DECIMAL(precision=13, scale=2))
    bar_brutto: float = Field(sa_column=DECIMAL(precision=13, scale=2))


class AbrechnungJahr(SQLModel, table=True):
    __tablename__ = "abrechnung_jahr"

    id: int | None = Field(default=None, primary_key=True)
    jahr: int = Field(nullable=False)
    abrechnung_tag_id_von: int = Field(foreign_key="abrechnung_tag.id", nullable=False)
    abrechnung_tag_id_bis: int = Field(foreign_key="abrechnung_tag.id", nullable=False)


class AbrechnungJahrMwst(SQLModel, table=True):
    __tablename__ = "abrechnung_jahr_mwst"

    id: int = Field(primary_key=True, foreign_key="abrechnung_jahr.id")
    mwst_satz: float = Field(sa_column=Column(DECIMAL(precision=6, scale=5), primary_key=True, nullable=False))
    mwst_netto: float = Field(sa_column=DECIMAL(precision=13, scale=2))
    mwst_betrag: float = Field(sa_column=DECIMAL(precision=13, scale=2))
    bar_brutto: float = Field(sa_column=DECIMAL(precision=13, scale=2))


class Zaehlprotokoll(SQLModel, table=True):
    __tablename__ = "zaehlprotokoll"

    id: int | None = Field(default=None, primary_key=True)
    abrechnung_tag_id: int = Field(foreign_key="abrechnung_tag.id", nullable=False)
    zeitpunkt: datetime = Field(sa_column=Column(TIMESTAMP, nullable=False))
    kommentar: str = Field(nullable=False)
    aktiv: bool = Field(nullable=False, default=True)
    user_id: int | None = Field(default=None, foreign_key="user.user_id")


class ZaehlprotokollDetails(SQLModel, table=True):
    __tablename__ = "zaehlprotokoll_details"

    id: int | None = Field(default=None, primary_key=True)
    zaehlprotokoll_id: int = Field(foreign_key="zaehlprotokoll.id", nullable=False)
    anzahl: int = Field(nullable=False, ge=0)
    einheit: float = Field(sa_column=DECIMAL(precision=13, scale=2), gt=0)


class Bestellung(SQLModel, table=True):
    __tablename__ = "bestellung"

    bestell_nr: int | None = Field(default=None, primary_key=True)
    typ: str = Field(max_length=12, nullable=False, default="")
    bestell_datum: datetime = Field(sa_column=Column(TIMESTAMP, nullable=False))
    jahr: int = Field(nullable=False, default=2000)
    kw: int = Field(nullable=False, default=1)
    user_id: int | None = Field(default=None, foreign_key="user.user_id")


class BestellungDetails(SQLModel, table=True):
    __tablename__ = "bestellung_details"

    bestell_nr: int = Field(foreign_key="bestellung.bestell_nr", primary_key=True)
    typ: str = Field(max_length=12, nullable=False, default="", primary_key=True)
    position: int = Field(primary_key=True)
    artikel_id: int = Field(foreign_key="artikel.artikel_id", nullable=False)
    stueckzahl: int = Field(nullable=False, default=1, ge=1)


class TSETransaction(SQLModel, table=True):
    __tablename__ = "tse_transaction"

    transaction_id: int | None = Field(default=None, primary_key=True)
    transaction_number: int | None = Field(default=None)
    rechnungs_nr: int | None = Field(default=None, foreign_key="verkauf.rechnungs_nr")
    training: bool = Field(nullable=False, default=False)
    transaction_start: str | None = Field(max_length=29, default=None)
    transaction_end: str | None = Field(max_length=29, default=None)
    process_type: str | None = Field(max_length=30, default=None)
    signature_counter: int | None = Field(default=None)
    signature_base64: str | None = Field(max_length=512, default=None)
    tse_error: str | None = Field(default=None)
    process_data: str | None = Field(max_length=65, default=None)
    user_id: int | None = Field(default=None, foreign_key="user.user_id")


class User(SQLModel, table=True):
    __tablename__ = "user"

    user_id: int | None = Field(default=None, primary_key=True)
    username: str = Field(max_length=50, nullable=False, unique=True)
    password_hash: str = Field(max_length=255, nullable=False)
    role: str = Field(max_length=20, nullable=False, default="mitarbeiter")  # admin | mitarbeiter
    active: bool = Field(nullable=False, default=True)

    anmeldungen: list["Anmeldung"] = Relationship(back_populates="user")


class Anmeldung(SQLModel, table=True):
    __tablename__ = "anmeldung"

    anmeldung_id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.user_id", nullable=False)
    login_time: datetime = Field(sa_column=Column(TIMESTAMP, nullable=False))
    logout_time: datetime | None = Field(default=None, sa_column=Column(TIMESTAMP, nullable=True))

    user: "User" = Relationship(back_populates="anmeldungen")


# Bestell-Typen like the Java POS: LM = Lebensmittel (order), KHW =
# Kunsthandwerk (order), IVT = Inventur (the order tables hold a stock count).
BESTELLUNG_TYPEN = ("LM", "KHW", "IVT")


# Ensure datetime values read from the database are always UTC-aware.
# MariaDB's Python connector (and SQLite) return naive datetimes even for
# TIMESTAMP columns, so we attach UTC tzinfo on load/refresh.
def _make_datetimes_aware(target):
    for key, value in list(getattr(target, "__dict__", {}).items()):
        if isinstance(value, datetime) and value.tzinfo is None:
            setattr(target, key, value.replace(tzinfo=timezone.utc))


@event.listens_for(SQLModel, "load", propagate=True)
def _on_load(target, context):
    _make_datetimes_aware(target)


@event.listens_for(SQLModel, "refresh", propagate=True)
def _on_refresh(target, context, attrs):
    _make_datetimes_aware(target)
