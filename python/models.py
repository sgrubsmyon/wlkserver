from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import DECIMAL, Column
from datetime import datetime

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
    mwst_satz: float = Field(sa_column=DECIMAL(precision=6, scale=5))
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
    wert: float | None = None


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
    mwst_id: int = Field(default=None, foreign_key="mwst.mwst_id") # sa_column_kwargs={"unsigned": True}, 
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
    mwst_id: int
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

    von: datetime | None = Field(nullable=True, default=None)
    bis: datetime | None = Field(nullable=True, default=None)
    aktiv: bool = Field(nullable=False, default=True)

    # relationships
    produktgruppe: "Produktgruppe" = Relationship(back_populates="artikel")
    lieferant: "Lieferant" = Relationship(back_populates="artikel")
    pfand: Pfand = Relationship(back_populates="artikel")
    rabattaktion: list["Rabattaktion"] = Relationship(back_populates="artikel")


# For reading articles
class ArtikelPublic(ArtikelBase):
    artikel_id: int
    produktgruppen_id: int
    lieferant_id: int
    produktgruppen_name: str
    lieferant_name: str

    von: datetime | None = Field()
    bis: datetime | None = Field()
    aktiv: bool = Field(nullable=False, default=True)


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
    von: datetime = Field(nullable=False)
    bis: datetime | None = Field(nullable=True, default=None)


# The table model
class Rabattaktion(RabattaktionBase, table=True):
    __tablename__ = 'rabattaktion'

    rabatt_id: int | None = Field(default=None, primary_key=True)

    produktgruppen_id: int | None = Field(default=None, foreign_key="produktgruppe.produktgruppen_id") # sa_column_kwargs={"unsigned": True},
    artikel_id: int | None = Field(default=None, foreign_key="artikel.artikel_id") # sa_column_kwargs={"unsigned": True},

    # relationships
    produktgruppe: "Produktgruppe" = Relationship(back_populates="rabattaktion")
    artikel: "Artikel" = Relationship(back_populates="rabattaktion")


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
    verkaufsdatum: datetime = Field(nullable=False)
    ec_zahlung: bool = Field(nullable=False, default=False)
    kunde_gibt: float | None = Field(sa_column=DECIMAL(precision=13, scale=2), default=None)


# The table model
class Verkauf(VerkaufBase, table=True):
    __tablename__ = 'verkauf'

    # primary key
    rechnungs_nr: int | None = Field(default=None, primary_key=True)

    # foreign keys
    storno_von: int | None = Field(default=None, foreign_key="verkauf.rechnungs_nr") # sa_column_kwargs={"unsigned": True},

    # relationships
    stornierter_verkauf: "Verkauf" = Relationship(back_populates="verkauf") # , sa_relationship_kwargs={"remote_side": "verkauf.rechnungs_nr"}


# For reading
class VerkaufPublic(VerkaufBase):
    rechnungs_nr: int
    storno_von: int | None


# For creating
class VerkaufCreate(VerkaufBase):
    storno_von: int | None = None


# The base model, shared by all
class verkaufMwstBase(SQLModel):
    mwst_netto: float = Field(sa_column=DECIMAL(precision=13, scale=2))
    mwst_betrag: float = Field(sa_column=DECIMAL(precision=13, scale=2))

# The table model
class verkaufMwst(verkaufMwstBase, table=True):
    __tablename__ = 'verkauf_mwst'

    # primary key
    rechnungs_nr: int = Field(nullable=False, primary_key=True, foreign_key="verkauf.rechnungs_nr")
    mwst_satz: float = Field(nullable=False, primary_key=True) # sa_column=DECIMAL(precision=6, scale=5), 

    # relationships
    verkauf: "Verkauf" = Relationship(back_populates="verkauf_mwst")


# For reading
class verkaufMwstPublic(verkaufMwstBase):
    rechnungs_nr: int
    mwst_satz: float


# For creating
class verkaufMwstCreate(verkaufMwstBase):
    rechnungs_nr: int
    mwst_satz: float


# The base model, shared by all
class verkaufDetailsBase(SQLModel):
    position: int | None = Field(default=None) # , sa_column_kwargs={"unsigned": True}
    stueckzahl: int = Field(nullable=False, default=1) # sa_column_kwargs={"unsigned": True},
    ges_preis: float = Field(sa_column=DECIMAL(precision=13, scale=2))
    mwst_satz: float = Field(sa_column=DECIMAL(precision=6, scale=5))


# The table model
class verkaufDetails(verkaufDetailsBase, table=True):
    __tablename__ = 'verkauf_details'

    # primary key
    vd_id: int | None = Field(default=None, primary_key=True)

    # foreign keys
    rechnungs_nr: int = Field(nullable=False, foreign_key="verkauf.rechnungs_nr") # sa_column_kwargs={"unsigned": True},
    artikel_id: int | None = Field(default=None, foreign_key="artikel.artikel_id") # sa_column_kwargs={"unsigned": True},
    rabatt_id: int | None = Field(default=None, foreign_key="rabattaktion.rabatt_id") # sa_column_kwargs={"unsigned": True},

    # relationships
    verkauf: "Verkauf" = Relationship(back_populates="verkauf_details")
    artikel: "Artikel" = Relationship(back_populates="verkauf_details")


# For reading
class verkaufDetailsPublic(verkaufDetailsBase):
    vd_id: int
    rechnungs_nr: int
    artikel_id: int | None
    artikel_name: str | None = None
    artikel_kurzname: str | None = None
    artikel_vk_preis: float | None = None


# For creating
class verkaufDetailsCreate(verkaufDetailsBase):
    rechnungs_nr: int
    artikel_id: int | None = None
    rabatt_id: int | None = None