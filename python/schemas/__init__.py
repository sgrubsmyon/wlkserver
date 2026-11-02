"""API schemas: request/response models, kept apart from the ORM tables."""
from datetime import date, datetime
from typing import Literal, Optional

from sqlmodel import Field, SQLModel

from ..models.tables import (
    ArtikelBase,
    LieferantBase,
    MwstBase,
    ProduktgruppeBase,
    RabattaktionBase,
    VerkaufBase,
    VerkaufDetailsBase,
    VerkaufMwstBase,
)


# For reading
class LieferantPublic(LieferantBase):
    lieferant_id: int
    n_artikel: int | None
    aktiv: bool


# For updating
class LieferantUpdate(SQLModel):
    lieferant_name: str | None = None
    lieferant_kurzname: str | None = None


# For reading
class MwstPublic(MwstBase):
    mwst_id: int


# For creating
class MwstCreate(SQLModel):
    mwst_satz: float = Field(ge=0, le=1)
    dsfinvk_ust_schluessel: int = Field(ge=0)
    dsfinvk_ust_beschr: str | None = Field(max_length=55, default=None)


# For updating
class MwstUpdate(SQLModel):
    mwst_satz: float | None = Field(ge=0, le=1, default=None)
    dsfinvk_ust_schluessel: int | None = Field(ge=0, default=None)
    dsfinvk_ust_beschr: str | None = Field(max_length=55, default=None)


# For reading
class PfandPublic(SQLModel):
    pfand_id: int
    artikel_id: int
    wert: float | None


# For creating
class PfandCreate(SQLModel):
    artikel_id: int


# For updating
class PfandUpdate(SQLModel):
    artikel_id: int | None = None


# For reading product groups
class ProduktgruppePublic(ProduktgruppeBase):
    produktgruppen_id: int
    mwst_id: int | None
    # OMG, this took me like a week to find out:
    # to avoid validation errors, we need to also allow nullable fields
    # in the response model to be None
    pfand_id: int | None

    aktiv: bool
    n_artikel: int | None
    n_artikel_rekursiv: int | None


# For creating product groups
class ProduktgruppeCreate(ProduktgruppeBase):
    mwst_id: int
    pfand_id: int | None = None


# For updating product groups
class ProduktgruppeUpdate(SQLModel):
    mwst_id: int | None = None
    pfand_id: int | None = None

    toplevel_id: int | None = None
    sub_id: int | None = None
    subsub_id: int | None = None
    produktgruppen_name: str | None = None
    std_einheit: str | None = None


# For reading articles
class ArtikelPublic(ArtikelBase):
    artikel_id: int
    produktgruppen_id: int
    lieferant_id: int
    produktgruppen_name: str
    lieferant_name: str
    pfand_artikel_id: int | None
    pfand_wert: float | None

    von: datetime | None
    bis: datetime | None
    aktiv: bool


# For creating articles
class ArtikelCreate(ArtikelBase):
    produktgruppen_id: int
    lieferant_id: int


# For updating articles
class ArtikelUpdate(SQLModel):
    produktgruppen_id: int | None = None
    lieferant_id: int | None = None

    artikel_nr: str | None = None
    artikel_name: str | None = None
    kurzname: str | None = None
    menge: float | None = Field(default=None, ge=0)
    einheit: str | None = None
    barcode: str | None = None
    herkunft: str | None = None
    vpe: int | None = None
    setgroesse: int | None = Field(default=None, ge=1)
    vk_preis: float | None = Field(default=None, ge=0)
    empf_vk_preis: float | None = Field(default=None, ge=0)
    ek_rabatt: float | None = Field(default=None, ge=0, le=1)
    ek_preis: float | None = Field(default=None, ge=0)
    variabler_preis: bool | None = None
    sortiment: bool | None = None
    lieferbar: bool | None = None
    beliebtheit: int | None = None
    bestand: int | None = None


# For reading
class RabattaktionPublic(RabattaktionBase):
    rabatt_id: int
    produktgruppen_id: int | None
    artikel_id: int | None
    produktgruppen_name: str | None = None
    artikel_name: str | None = None


# For creating
class RabattaktionCreate(RabattaktionBase):
    produktgruppen_id: int | None = None
    artikel_id: int | None = None


# For updating
class RabattaktionUpdate(SQLModel):
    produktgruppen_id: int | None = None
    artikel_id: int | None = None

    aktionsname: str | None = None
    rabatt_relativ: float | None = Field(default=None, ge=0, le=1)
    rabatt_absolut: float | None = Field(default=None, ge=0)
    mengenrabatt_schwelle: int | None = Field(default=None, ge=1)
    mengenrabatt_anzahl_kostenlos: int | None = Field(default=None, ge=1)
    mengenrabatt_relativ: float | None = Field(default=None, ge=0, le=1)
    von: datetime | None = None
    bis: datetime | None = None


# For reading
class VerkaufPublic(VerkaufBase):
    rechnungs_nr: int
    verkaufsdatum: datetime
    storno_von: int | None
    ec_warning: str | None = None
    change: float | None = None


# For creating
class VerkaufCreate(VerkaufBase):
    storno_von: int | None = None
    # Receipt-level discount (Java "Rabatt auf Rechnung"), e.g. 0.1 = 10 %.
    rechnung_rabatt_relativ: float | None = Field(default=None, ge=0, lt=1)
    # Voucher redemption as a sale position (Java `gutscheinEinloesungHinzufuegen`).
    gutschein_einloesung_nr: int | None = None
    gutschein_einloesung_betrag: float | None = Field(default=None, gt=0)
    # New deposit: split this amount across the basket's VAT rates and zero the
    # other positions (Java `anzahlungHinzufuegen`).
    anzahlung_betrag: float | None = Field(default=None, gt=0)
    # Resolve an open deposit: re-add its positions and book the negative
    # Anzahlungsauflösung line (Java `AnzahlungAufloesDialog`).
    anzahlung_aufloesen_nr: int | None = None
    # TSE transaction started with the first article of this basket. The sale
    # finishes it (Java `Kassieren.startTransaction` on the first item).
    tse_transaction_id: int | None = None
    verkauf_details: list["VerkaufDetailsCreate"] | None = None


# For reading
class VerkaufMwstPublic(VerkaufMwstBase):
    rechnungs_nr: int
    mwst_satz: float


# For creating
class VerkaufMwstCreate(VerkaufMwstBase):
    mwst_satz: float


# For reading
class VerkaufDetailsPublic(VerkaufDetailsBase):
    vd_id: int
    ges_preis: float
    mwst_satz: float
    rechnungs_nr: int
    artikel_id: int | None
    rabatt_id: int | None
    artikel_name: str | None = None
    artikel_kurzname: str | None = None
    aktionsname: str | None = None


# For creating
class VerkaufDetailsCreate(VerkaufDetailsBase):
    artikel_id: int | None = None
    rabatt_id: int | None = None
    # Manual per-line discount; negative values are a price increase (Aufschlag).
    rabatt_absolut: float | None = None
    # Explicit line total (e.g. `variabler_preis` articles); defaults to the
    # article price times the quantity.
    ges_preis: float | None = Field(default=None, ge=0)


class KassenstandPublic(SQLModel):
    kassenstand_id: int
    buchungsdatum: datetime
    neuer_kassenstand: float
    manuell: bool
    entnahme: bool
    rechnungs_nr: int | None
    kommentar: str | None


class KassenstandCreate(SQLModel):
    buchungsdatum: datetime | None = None
    neuer_kassenstand: float = Field(ge=0)
    manuell: bool = False
    entnahme: bool = False
    rechnungs_nr: int | None = None
    kommentar: str | None = Field(max_length=70, default=None)


class GutscheinPublic(SQLModel):
    gutschein_id: int
    gutschein_nr: int
    datum: datetime
    gutschein_in_vd_id: int | None
    einloesung_in_vd_id: int | None
    restbetrag: float
    restbetrag_anfang: float | None = None


class GutscheinCreate(SQLModel):
    # `gutschein_nr` is assigned by the backend (MAX + 1), never by the client.
    datum: datetime | None = None
    gutschein_in_vd_id: int | None = None
    einloesung_in_vd_id: int | None = None
    restbetrag: float = Field(ge=0)


class GutscheinEinloesen(SQLModel):
    datum: datetime | None = None
    gutschein_in_vd_id: int | None = None
    einloesung_in_vd_id: int | None = None
    restbetrag: float | None = None
    betrag: float | None = None


class AnzahlungPublic(SQLModel):
    anzahlung_id: int
    datum: datetime
    anzahlung_in_rech_nr: int
    aufloesung_in_rech_nr: int | None


class AnzahlungCreate(SQLModel):
    datum: datetime | None = None
    anzahlung_in_rech_nr: int
    aufloesung_in_rech_nr: int | None = None
    details: list["AnzahlungDetailsCreate"] | None = None


class AnzahlungDetailsPublic(SQLModel):
    ad_id: int
    rechnungs_nr: int
    vd_id: int
    ges_preis: float


class AnzahlungDetailsCreate(SQLModel):
    rechnungs_nr: int
    vd_id: int
    ges_preis: float


class AnzahlungAufloesen(SQLModel):
    datum: datetime | None = None
    aufloesung_in_rech_nr: int


class AbrechnungTagPublic(SQLModel):
    id: int
    z_kasse_id: str
    zeitpunkt: datetime
    zeitpunkt_real: datetime
    kassenstand_id: int | None
    rechnungs_nr_von: int
    rechnungs_nr_bis: int
    last_tse_sig_counter: int | None
    user_id: int | None = None
    storno_summe: float | None = None
    retouren_summe: float | None = None
    mwst_nach_id: dict | None = None


class AbrechnungTagCreate(SQLModel):
    z_kasse_id: str | None = None
    zeitpunkt: datetime | None = None
    zeitpunkt_real: datetime | None = None
    kassenstand_id: int | None = None
    rechnungs_nr_von: int | None = None
    rechnungs_nr_bis: int | None = None
    last_tse_sig_counter: int | None = None
    # Count recorded before/while submitting the settlement (Java
    # AbrechnungenTag.insertZaehlprotokoll); inserted after the settlement.
    zaehlprotokoll: "ZaehlprotokollCreate | None" = None


class AbrechnungTagMwstPublic(SQLModel):
    id: int
    mwst_satz: float
    mwst_netto: float
    mwst_betrag: float
    bar_brutto: float


class AbrechnungMonatPublic(SQLModel):
    id: int
    monat: date
    abrechnung_tag_id_von: int
    abrechnung_tag_id_bis: int


class AbrechnungMonatCreate(SQLModel):
    monat: str | None = None
    abrechnung_tag_id_von: int | None = None
    abrechnung_tag_id_bis: int | None = None


class AbrechnungMonatMwstPublic(SQLModel):
    id: int
    mwst_satz: float
    mwst_netto: float
    mwst_betrag: float
    bar_brutto: float


class AbrechnungJahrPublic(SQLModel):
    id: int
    jahr: int
    abrechnung_tag_id_von: int
    abrechnung_tag_id_bis: int


class AbrechnungJahrCreate(SQLModel):
    jahr: int | None = None
    abrechnung_tag_id_von: int | None = None
    abrechnung_tag_id_bis: int | None = None


class AbrechnungJahrMwstPublic(SQLModel):
    id: int
    mwst_satz: float
    mwst_netto: float
    mwst_betrag: float
    bar_brutto: float


class ZaehlprotokollPublic(SQLModel):
    id: int
    abrechnung_tag_id: int
    zeitpunkt: datetime
    kommentar: str
    aktiv: bool


class ZaehlprotokollCreate(SQLModel):
    # Optional here because the count is submitted with POST /abrechnung/tag
    # before the settlement row exists; POST /zaehlprotokoll still requires it.
    abrechnung_tag_id: int | None = None
    zeitpunkt: datetime | None = None
    kommentar: str
    aktiv: bool = True
    details: list["ZaehlprotokollDetailsCreate"] | None = None


class ZaehlprotokollUpdate(SQLModel):
    zeitpunkt: datetime | None = None
    kommentar: str | None = None
    aktiv: bool | None = None


class ZaehlprotokollDetailsPublic(SQLModel):
    id: int
    zaehlprotokoll_id: int
    anzahl: int
    einheit: float


class ZaehlprotokollDetailsCreate(SQLModel):
    anzahl: int = Field(ge=0)
    einheit: float = Field(gt=0)


class BestellungPublic(SQLModel):
    bestell_nr: int
    typ: str
    bestell_datum: datetime
    jahr: int
    kw: int


class BestellungCreate(SQLModel):
    typ: Literal["LM", "KHW", "IVT"] | None = None
    bestell_datum: datetime | None = None
    jahr: int | None = None
    kw: int | None = None
    details: list["BestellungDetailsCreate"] | None = None


class BestellungUpdate(SQLModel):
    typ: Literal["LM", "KHW", "IVT"] | None = None
    bestell_datum: datetime | None = None
    jahr: int | None = None
    kw: int | None = None
    details: list["BestellungDetailsCreate"] | None = None


class BestellungDetailsPublic(SQLModel):
    bestell_nr: int
    typ: str
    position: int
    artikel_id: int
    stueckzahl: int


class BestellungDetailsCreate(SQLModel):
    bestell_nr: int | None = None
    typ: str | None = None
    position: int
    artikel_id: int
    stueckzahl: int = Field(default=1, ge=1)


class TSETransactionPublic(SQLModel):
    transaction_id: int
    transaction_number: int | None
    rechnungs_nr: int | None
    training: bool
    transaction_start: str | None
    transaction_end: str | None
    process_type: str | None
    signature_counter: int | None
    signature_base64: str | None
    tse_error: str | None
    process_data: str | None


class TSETransactionCreate(SQLModel):
    transaction_number: int | None = None
    rechnungs_nr: int | None = None
    training: bool = False
    transaction_start: str | None = None
    transaction_end: str | None = None
    process_type: str | None = None
    signature_counter: int | None = None
    signature_base64: str | None = None
    tse_error: str | None = None
    process_data: str | None = None


class UserPublic(SQLModel):
    user_id: int
    username: str
    role: str
    active: bool


class UserCreate(SQLModel):
    username: str = Field(max_length=50)
    password: str = Field(min_length=1)
    role: Literal["admin", "mitarbeiter"] = Field(default="mitarbeiter")
    active: bool = Field(default=True)


class UserUpdate(SQLModel):
    username: str | None = None
    role: Literal["admin", "mitarbeiter"] | None = None
    active: bool | None = None
    password: str | None = None


class AnmeldungPublic(SQLModel):
    anmeldung_id: int
    user_id: int
    login_time: datetime
    logout_time: datetime | None
