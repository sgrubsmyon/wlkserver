from typing import Optional

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import DECIMAL, Column, TIMESTAMP, event, DATE
from sqlalchemy.orm import backref
from datetime import datetime, timezone, date

#######################
# Lieferant models
#######################

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


# For reading
class LieferantPublic(LieferantBase):
    lieferant_id: int
    n_artikel: int | None
    aktiv: bool


# For updating
class LieferantUpdate(SQLModel):
    lieferant_name: str | None = None
    lieferant_kurzname: str | None = None


#######################
# MwSt models
#######################

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


#######################
# Pfand models
#######################

class Pfand(SQLModel, table=True):
    __tablename__ = 'pfand'

    pfand_id: int | None = Field(default=None, primary_key=True)
    artikel_id: int = Field(foreign_key="artikel.artikel_id") # sa_column_kwargs={"unsigned": True},

    artikel: "Artikel" = Relationship(back_populates="pfand")
    produktgruppe: list["Produktgruppe"] = Relationship(back_populates="pfand")


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


#######################
# Produktgruppe models
#######################

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


#################
# Artikel models
#################

# The base model, shared by all
class ArtikelBase(SQLModel):
    artikel_nr: str = Field(max_length=30, nullable=False)
    artikel_name: str = Field(max_length=180, nullable=False)
    kurzname: str | None = Field(max_length=50, default=None)
    menge: float | None = Field(sa_column=DECIMAL(precision=8, scale=5), default=None)
    einheit: str | None = Field(max_length=10, default=None)
    barcode: str | None = Field(max_length=30, default=None)
    herkunft: str | None = Field(max_length=100, default=None)
    vpe: int | None = Field(default=None) # sa_column_kwargs={"unsigned": True}
    setgroesse: int = Field(nullable=False, default=1) # sa_column_kwargs={"unsigned": True}, 
    vk_preis: float | None = Field(sa_column=DECIMAL(precision=13, scale=2), default=None)
    empf_vk_preis: float | None = Field(sa_column=DECIMAL(precision=13, scale=2), default=None)
    ek_rabatt: float | None = Field(sa_column=DECIMAL(precision=6, scale=5), default=None)
    ek_preis: float | None = Field(sa_column=DECIMAL(precision=13, scale=2), default=None)
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
    menge: float | None = None
    einheit: str | None = None
    barcode: str | None = None
    herkunft: str | None = None
    vpe: int | None = None
    setgroesse: int | None = None
    vk_preis: float | None = None
    empf_vk_preis: float | None = None
    ek_rabatt: float | None = None
    ek_preis: float | None = None
    variabler_preis: bool | None = None
    sortiment: bool | None = None
    lieferbar: bool | None = None
    beliebtheit: int | None = None
    bestand: int | None = None


######################
# Rabattaktion models
######################

# The base model, shared by all
class RabattaktionBase(SQLModel):
    aktionsname: str = Field(max_length=50, default=None)
    rabatt_relativ: float | None = Field(sa_column=DECIMAL(precision=6, scale=5), default=None)
    rabatt_absolut: float | None = Field(sa_column=DECIMAL(precision=13, scale=2), default=None)
    mengenrabatt_schwelle: int | None = Field(default=None) # sa_column_kwargs={"unsigned": True}
    mengenrabatt_anzahl_kostenlos: int | None = Field(default=None) # sa_column_kwargs={"unsigned": True}
    mengenrabatt_relativ: float | None = Field(sa_column=DECIMAL(precision=6, scale=5), default=None)
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
    rabatt_relativ: float | None = None
    rabatt_absolut: float | None = None
    mengenrabatt_schwelle: int | None = None
    mengenrabatt_anzahl_kostenlos: int | None = None
    mengenrabatt_relativ: float | None = None
    von: datetime | None = None
    bis: datetime | None = None


######################
# Verkauf models
######################

# The base model, shared by all
class VerkaufBase(SQLModel):
    ec_zahlung: bool = Field(nullable=False, default=False)
    kunde_gibt: float | None = Field(sa_column=DECIMAL(precision=13, scale=2), default=None)
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


# For reading
class VerkaufPublic(VerkaufBase):
    rechnungs_nr: int
    verkaufsdatum: datetime
    storno_von: int | None
    ec_warning: str | None = None


# For creating
class VerkaufCreate(VerkaufBase):
    storno_von: int | None = None
    verkauf_details: list["VerkaufDetailsCreate"] | None = None

#########################

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


# For reading
class VerkaufMwstPublic(VerkaufMwstBase):
    rechnungs_nr: int
    mwst_satz: float


# For creating
class VerkaufMwstCreate(VerkaufMwstBase):
    mwst_satz: float

#########################

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


#######################
# Kassenstand models
#######################

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


#######################
# Gutschein models
#######################

class Gutschein(SQLModel, table=True):
    __tablename__ = "gutschein"

    gutschein_id: int | None = Field(default=None, primary_key=True)
    gutschein_nr: int = Field(nullable=False)
    datum: datetime = Field(sa_column=Column(TIMESTAMP, nullable=False))
    gutschein_in_vd_id: int | None = Field(default=None, foreign_key="verkauf_details.vd_id")
    einloesung_in_vd_id: int | None = Field(default=None, foreign_key="verkauf_details.vd_id")
    restbetrag: float = Field(ge=0, sa_column=DECIMAL(precision=13, scale=2))
    user_id: int | None = Field(default=None, foreign_key="user.user_id")


class GutscheinPublic(SQLModel):
    gutschein_id: int
    gutschein_nr: int
    datum: datetime
    gutschein_in_vd_id: int | None
    einloesung_in_vd_id: int | None
    restbetrag: float


class GutscheinCreate(SQLModel):
    gutschein_nr: int
    datum: datetime | None = None
    gutschein_in_vd_id: int | None = None
    einloesung_in_vd_id: int | None = None
    restbetrag: float


class GutscheinEinloesen(SQLModel):
    datum: datetime | None = None
    gutschein_in_vd_id: int | None = None
    einloesung_in_vd_id: int | None = None
    restbetrag: float | None = None
    betrag: float | None = None


#######################
# Anzahlung models
#######################

class Anzahlung(SQLModel, table=True):
    __tablename__ = "anzahlung"

    anzahlung_id: int | None = Field(default=None, primary_key=True)
    datum: datetime = Field(sa_column=Column(TIMESTAMP, nullable=False))
    anzahlung_in_rech_nr: int = Field(foreign_key="verkauf.rechnungs_nr", nullable=False)
    aufloesung_in_rech_nr: int | None = Field(default=None, foreign_key="verkauf.rechnungs_nr")
    user_id: int | None = Field(default=None, foreign_key="user.user_id")


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


class AnzahlungDetails(SQLModel, table=True):
    __tablename__ = "anzahlung_details"

    ad_id: int | None = Field(default=None, primary_key=True)
    rechnungs_nr: int = Field(foreign_key="verkauf.rechnungs_nr", nullable=False)
    vd_id: int = Field(foreign_key="verkauf_details.vd_id", nullable=False)
    ges_preis: float = Field(sa_column=DECIMAL(precision=13, scale=2))


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


#######################
# Abrechnung Tag models
#######################

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


class AbrechnungTagPublic(SQLModel):
    id: int
    z_kasse_id: str
    zeitpunkt: datetime
    zeitpunkt_real: datetime
    kassenstand_id: int | None
    rechnungs_nr_von: int
    rechnungs_nr_bis: int
    last_tse_sig_counter: int | None


class AbrechnungTagCreate(SQLModel):
    z_kasse_id: str | None = None
    zeitpunkt: datetime | None = None
    zeitpunkt_real: datetime | None = None
    kassenstand_id: int | None = None
    rechnungs_nr_von: int | None = None
    rechnungs_nr_bis: int | None = None
    last_tse_sig_counter: int | None = None


class AbrechnungTagMwst(SQLModel, table=True):
    __tablename__ = "abrechnung_tag_mwst"

    id: int = Field(primary_key=True, foreign_key="abrechnung_tag.id")
    mwst_satz: float = Field(sa_column=Column(DECIMAL(precision=6, scale=5), primary_key=True, nullable=False))
    mwst_netto: float = Field(sa_column=DECIMAL(precision=13, scale=2))
    mwst_betrag: float = Field(sa_column=DECIMAL(precision=13, scale=2))
    bar_brutto: float = Field(sa_column=DECIMAL(precision=13, scale=2))


class AbrechnungTagMwstPublic(SQLModel):
    id: int
    mwst_satz: float
    mwst_netto: float
    mwst_betrag: float
    bar_brutto: float


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


#######################
# Abrechnung Monat models
#######################

class AbrechnungMonat(SQLModel, table=True):
    __tablename__ = "abrechnung_monat"

    id: int | None = Field(default=None, primary_key=True)
    monat: date = Field(sa_column=Column(DATE, nullable=False))
    abrechnung_tag_id_von: int = Field(foreign_key="abrechnung_tag.id", nullable=False)
    abrechnung_tag_id_bis: int = Field(foreign_key="abrechnung_tag.id", nullable=False)


class AbrechnungMonatPublic(SQLModel):
    id: int
    monat: date
    abrechnung_tag_id_von: int
    abrechnung_tag_id_bis: int


class AbrechnungMonatCreate(SQLModel):
    monat: str | None = None
    abrechnung_tag_id_von: int | None = None
    abrechnung_tag_id_bis: int | None = None


class AbrechnungMonatMwst(SQLModel, table=True):
    __tablename__ = "abrechnung_monat_mwst"

    id: int = Field(primary_key=True, foreign_key="abrechnung_monat.id")
    mwst_satz: float = Field(sa_column=Column(DECIMAL(precision=6, scale=5), primary_key=True, nullable=False))
    mwst_netto: float = Field(sa_column=DECIMAL(precision=13, scale=2))
    mwst_betrag: float = Field(sa_column=DECIMAL(precision=13, scale=2))
    bar_brutto: float = Field(sa_column=DECIMAL(precision=13, scale=2))


class AbrechnungMonatMwstPublic(SQLModel):
    id: int
    mwst_satz: float
    mwst_netto: float
    mwst_betrag: float
    bar_brutto: float


#######################
# Abrechnung Jahr models
#######################

class AbrechnungJahr(SQLModel, table=True):
    __tablename__ = "abrechnung_jahr"

    id: int | None = Field(default=None, primary_key=True)
    jahr: int = Field(nullable=False)
    abrechnung_tag_id_von: int = Field(foreign_key="abrechnung_tag.id", nullable=False)
    abrechnung_tag_id_bis: int = Field(foreign_key="abrechnung_tag.id", nullable=False)


class AbrechnungJahrPublic(SQLModel):
    id: int
    jahr: int
    abrechnung_tag_id_von: int
    abrechnung_tag_id_bis: int


class AbrechnungJahrCreate(SQLModel):
    jahr: int | None = None
    abrechnung_tag_id_von: int | None = None
    abrechnung_tag_id_bis: int | None = None


class AbrechnungJahrMwst(SQLModel, table=True):
    __tablename__ = "abrechnung_jahr_mwst"

    id: int = Field(primary_key=True, foreign_key="abrechnung_jahr.id")
    mwst_satz: float = Field(sa_column=Column(DECIMAL(precision=6, scale=5), primary_key=True, nullable=False))
    mwst_netto: float = Field(sa_column=DECIMAL(precision=13, scale=2))
    mwst_betrag: float = Field(sa_column=DECIMAL(precision=13, scale=2))
    bar_brutto: float = Field(sa_column=DECIMAL(precision=13, scale=2))


class AbrechnungJahrMwstPublic(SQLModel):
    id: int
    mwst_satz: float
    mwst_netto: float
    mwst_betrag: float
    bar_brutto: float


#######################
# Zaehlprotokoll models
#######################

class Zaehlprotokoll(SQLModel, table=True):
    __tablename__ = "zaehlprotokoll"

    id: int | None = Field(default=None, primary_key=True)
    abrechnung_tag_id: int = Field(foreign_key="abrechnung_tag.id", nullable=False)
    zeitpunkt: datetime = Field(sa_column=Column(TIMESTAMP, nullable=False))
    kommentar: str = Field(nullable=False)
    aktiv: bool = Field(nullable=False, default=True)
    user_id: int | None = Field(default=None, foreign_key="user.user_id")


class ZaehlprotokollPublic(SQLModel):
    id: int
    abrechnung_tag_id: int
    zeitpunkt: datetime
    kommentar: str
    aktiv: bool


class ZaehlprotokollCreate(SQLModel):
    abrechnung_tag_id: int
    zeitpunkt: datetime | None = None
    kommentar: str
    aktiv: bool = True
    details: list["ZaehlprotokollDetailsCreate"] | None = None


class ZaehlprotokollUpdate(SQLModel):
    zeitpunkt: datetime | None = None
    kommentar: str | None = None
    aktiv: bool | None = None


class ZaehlprotokollDetails(SQLModel, table=True):
    __tablename__ = "zaehlprotokoll_details"

    id: int | None = Field(default=None, primary_key=True)
    zaehlprotokoll_id: int = Field(foreign_key="zaehlprotokoll.id", nullable=False)
    anzahl: int = Field(nullable=False)
    einheit: float = Field(sa_column=DECIMAL(precision=13, scale=2))


class ZaehlprotokollDetailsPublic(SQLModel):
    id: int
    zaehlprotokoll_id: int
    anzahl: int
    einheit: float


class ZaehlprotokollDetailsCreate(SQLModel):
    anzahl: int
    einheit: float


#######################
# Bestellung models
#######################

class Bestellung(SQLModel, table=True):
    __tablename__ = "bestellung"

    bestell_nr: int | None = Field(default=None, primary_key=True)
    typ: str = Field(max_length=12, nullable=False, default="")
    bestell_datum: datetime = Field(sa_column=Column(TIMESTAMP, nullable=False))
    jahr: int = Field(nullable=False, default=2000)
    kw: int = Field(nullable=False, default=1)
    user_id: int | None = Field(default=None, foreign_key="user.user_id")


class BestellungPublic(SQLModel):
    bestell_nr: int
    typ: str
    bestell_datum: datetime
    jahr: int
    kw: int


class BestellungCreate(SQLModel):
    typ: str | None = None
    bestell_datum: datetime | None = None
    jahr: int | None = None
    kw: int | None = None


class BestellungUpdate(SQLModel):
    typ: str | None = None
    bestell_datum: datetime | None = None
    jahr: int | None = None
    kw: int | None = None


class BestellungDetails(SQLModel, table=True):
    __tablename__ = "bestellung_details"

    bestell_nr: int = Field(foreign_key="bestellung.bestell_nr", primary_key=True)
    typ: str = Field(max_length=12, nullable=False, default="", primary_key=True)
    position: int = Field(primary_key=True)
    artikel_id: int = Field(foreign_key="artikel.artikel_id", nullable=False)
    stueckzahl: int = Field(nullable=False, default=1)


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
    stueckzahl: int = 1


#######################
# TSE transaction models
#######################

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


#######################
# User / Auth models (Phase 7.4)
#######################

class User(SQLModel, table=True):
    __tablename__ = "user"

    user_id: int | None = Field(default=None, primary_key=True)
    username: str = Field(max_length=50, nullable=False, unique=True)
    password_hash: str = Field(max_length=255, nullable=False)
    role: str = Field(max_length=20, nullable=False, default="mitarbeiter")  # admin | mitarbeiter
    active: bool = Field(nullable=False, default=True)

    anmeldungen: list["Anmeldung"] = Relationship(back_populates="user")


class UserPublic(SQLModel):
    user_id: int
    username: str
    role: str
    active: bool


class UserCreate(SQLModel):
    username: str = Field(max_length=50)
    password: str
    role: str = Field(default="mitarbeiter")
    active: bool = Field(default=True)


class UserUpdate(SQLModel):
    username: str | None = None
    role: str | None = None
    active: bool | None = None
    password: str | None = None


class Anmeldung(SQLModel, table=True):
    __tablename__ = "anmeldung"

    anmeldung_id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.user_id", nullable=False)
    login_time: datetime = Field(sa_column=Column(TIMESTAMP, nullable=False))
    logout_time: datetime | None = Field(default=None, sa_column=Column(TIMESTAMP, nullable=True))

    user: "User" = Relationship(back_populates="anmeldungen")


#######################
# Training table models (training mode)
#######################

class TrainingVerkauf(SQLModel, table=True):
    __tablename__ = "training_verkauf"
    rechnungs_nr: int | None = Field(default=None, primary_key=True)
    verkaufsdatum: datetime = Field(sa_column=Column(TIMESTAMP, nullable=False))
    storno_von: int | None = Field(default=None, foreign_key="training_verkauf.rechnungs_nr")
    ec_zahlung: bool = Field(nullable=False, default=False)
    kunde_gibt: float | None = Field(sa_column=DECIMAL(precision=13, scale=2), default=None)


class TrainingVerkaufMwst(SQLModel, table=True):
    __tablename__ = "training_verkauf_mwst"
    rechnungs_nr: int = Field(foreign_key="training_verkauf.rechnungs_nr", primary_key=True)
    mwst_satz: float = Field(sa_column=Column(DECIMAL(precision=6, scale=5), primary_key=True, nullable=False))
    mwst_netto: float = Field(sa_column=DECIMAL(precision=13, scale=2))
    mwst_betrag: float = Field(sa_column=DECIMAL(precision=13, scale=2))


class TrainingVerkaufDetails(SQLModel, table=True):
    __tablename__ = "training_verkauf_details"
    vd_id: int | None = Field(default=None, primary_key=True)
    rechnungs_nr: int = Field(foreign_key="training_verkauf.rechnungs_nr", nullable=False)
    position: int | None = Field(default=None)
    artikel_id: int | None = Field(default=None, foreign_key="artikel.artikel_id")
    rabatt_id: int | None = Field(default=None, foreign_key="rabattaktion.rabatt_id")
    stueckzahl: int = Field(nullable=False, default=1)
    ges_preis: float = Field(sa_column=DECIMAL(precision=13, scale=2))
    mwst_satz: float = Field(sa_column=DECIMAL(precision=6, scale=5))


class TrainingKassenstand(SQLModel, table=True):
    __tablename__ = "training_kassenstand"
    kassenstand_id: int | None = Field(default=None, primary_key=True)
    buchungsdatum: datetime = Field(sa_column=Column(TIMESTAMP, nullable=False))
    neuer_kassenstand: float = Field(sa_column=DECIMAL(precision=13, scale=2))
    manuell: bool = Field(nullable=False, default=False)
    entnahme: bool = Field(nullable=False, default=False)
    rechnungs_nr: int | None = Field(default=None, foreign_key="training_verkauf.rechnungs_nr")
    kommentar: str | None = Field(max_length=70, default=None)


class TrainingAnzahlung(SQLModel, table=True):
    __tablename__ = "training_anzahlung"
    anzahlung_id: int | None = Field(default=None, primary_key=True)
    datum: datetime = Field(sa_column=Column(TIMESTAMP, nullable=False))
    anzahlung_in_rech_nr: int = Field(foreign_key="training_verkauf.rechnungs_nr", nullable=False)
    aufloesung_in_rech_nr: int | None = Field(default=None, foreign_key="training_verkauf.rechnungs_nr")


class TrainingAnzahlungDetails(SQLModel, table=True):
    __tablename__ = "training_anzahlung_details"
    ad_id: int | None = Field(default=None, primary_key=True)
    rechnungs_nr: int = Field(foreign_key="training_verkauf.rechnungs_nr", nullable=False)
    vd_id: int = Field(foreign_key="training_verkauf_details.vd_id", nullable=False)
    ges_preis: float = Field(sa_column=DECIMAL(precision=13, scale=2))


class TrainingGutschein(SQLModel, table=True):
    __tablename__ = "training_gutschein"
    gutschein_id: int | None = Field(default=None, primary_key=True)
    gutschein_nr: int = Field(nullable=False)
    datum: datetime = Field(sa_column=Column(TIMESTAMP, nullable=False))
    gutschein_in_vd_id: int | None = Field(default=None, foreign_key="training_verkauf_details.vd_id")
    einloesung_in_vd_id: int | None = Field(default=None, foreign_key="training_verkauf_details.vd_id")
    restbetrag: float = Field(sa_column=DECIMAL(precision=13, scale=2))


class TrainingAbrechnungTag(SQLModel, table=True):
    __tablename__ = "training_abrechnung_tag"
    id: int | None = Field(default=None, primary_key=True)
    z_kasse_id: str = Field(max_length=30, nullable=False)
    zeitpunkt: datetime = Field(sa_column=Column(TIMESTAMP, nullable=False))
    zeitpunkt_real: datetime = Field(sa_column=Column(TIMESTAMP, nullable=False))
    kassenstand_id: int | None = Field(default=None, foreign_key="training_kassenstand.kassenstand_id")
    rechnungs_nr_von: int = Field(foreign_key="training_verkauf.rechnungs_nr", nullable=False)
    rechnungs_nr_bis: int = Field(foreign_key="training_verkauf.rechnungs_nr", nullable=False)
    last_tse_sig_counter: int | None = Field(default=None)


class TrainingAbrechnungTagMwst(SQLModel, table=True):
    __tablename__ = "training_abrechnung_tag_mwst"
    id: int = Field(primary_key=True, foreign_key="training_abrechnung_tag.id")
    mwst_satz: float = Field(sa_column=Column(DECIMAL(precision=6, scale=5), primary_key=True, nullable=False))
    mwst_netto: float = Field(sa_column=DECIMAL(precision=13, scale=2))
    mwst_betrag: float = Field(sa_column=DECIMAL(precision=13, scale=2))
    bar_brutto: float = Field(sa_column=DECIMAL(precision=13, scale=2))


class TrainingZaehlprotokoll(SQLModel, table=True):
    __tablename__ = "training_zaehlprotokoll"
    id: int | None = Field(default=None, primary_key=True)
    abrechnung_tag_id: int = Field(foreign_key="training_abrechnung_tag.id", nullable=False)
    zeitpunkt: datetime = Field(sa_column=Column(TIMESTAMP, nullable=False))
    kommentar: str = Field(nullable=False)
    aktiv: bool = Field(nullable=False, default=True)


class TrainingZaehlprotokollDetails(SQLModel, table=True):
    __tablename__ = "training_zaehlprotokoll_details"
    id: int | None = Field(default=None, primary_key=True)
    zaehlprotokoll_id: int = Field(foreign_key="training_zaehlprotokoll.id", nullable=False)
    anzahl: int = Field(nullable=False)
    einheit: float = Field(sa_column=DECIMAL(precision=13, scale=2))


class TrainingAbrechnungMonat(SQLModel, table=True):
    __tablename__ = "training_abrechnung_monat"
    id: int | None = Field(default=None, primary_key=True)
    monat: date = Field(nullable=False)
    abrechnung_tag_id_von: int = Field(foreign_key="training_abrechnung_tag.id", nullable=False)
    abrechnung_tag_id_bis: int = Field(foreign_key="training_abrechnung_tag.id", nullable=False)


class TrainingAbrechnungMonatMwst(SQLModel, table=True):
    __tablename__ = "training_abrechnung_monat_mwst"
    id: int = Field(primary_key=True, foreign_key="training_abrechnung_monat.id")
    mwst_satz: float = Field(sa_column=Column(DECIMAL(precision=6, scale=5), primary_key=True, nullable=False))
    mwst_netto: float = Field(sa_column=DECIMAL(precision=13, scale=2))
    mwst_betrag: float = Field(sa_column=DECIMAL(precision=13, scale=2))
    bar_brutto: float = Field(sa_column=DECIMAL(precision=13, scale=2))


class TrainingAbrechnungJahr(SQLModel, table=True):
    __tablename__ = "training_abrechnung_jahr"
    id: int | None = Field(default=None, primary_key=True)
    jahr: int = Field(nullable=False)
    abrechnung_tag_id_von: int = Field(foreign_key="training_abrechnung_tag.id", nullable=False)
    abrechnung_tag_id_bis: int = Field(foreign_key="training_abrechnung_tag.id", nullable=False)


class TrainingAbrechnungJahrMwst(SQLModel, table=True):
    __tablename__ = "training_abrechnung_jahr_mwst"
    id: int = Field(primary_key=True, foreign_key="training_abrechnung_jahr.id")
    mwst_satz: float = Field(sa_column=Column(DECIMAL(precision=6, scale=5), primary_key=True, nullable=False))
    mwst_netto: float = Field(sa_column=DECIMAL(precision=13, scale=2))
    mwst_betrag: float = Field(sa_column=DECIMAL(precision=13, scale=2))
    bar_brutto: float = Field(sa_column=DECIMAL(precision=13, scale=2))
