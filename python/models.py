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
    kurzname: str | None = Field(max_length=50)
    menge: float | None = Field(sa_column=DECIMAL(precision=8, scale=5))
    einheit: str | None = Field(max_length=10)
    barcode: str | None = Field(max_length=30)
    herkunft: str | None = Field(max_length=100)
    vpe: int | None # sa_column_kwargs={"unsigned": True}
    setgroesse: int = Field(nullable=False, default=1) # sa_column_kwargs={"unsigned": True}, 
    vk_preis: float | None = Field(sa_column=DECIMAL(precision=13, scale=2))
    empf_vk_preis: float | None = Field(sa_column=DECIMAL(precision=13, scale=2))
    ek_rabatt: float | None = Field(sa_column=DECIMAL(precision=6, scale=5))
    ek_preis: float | None = Field(sa_column=DECIMAL(precision=13, scale=2))
    variabler_preis: bool = Field(nullable=False, default=False)
    sortiment: bool = Field(nullable=False, default=False)
    lieferbar: bool = Field(nullable=False, default=False)
    beliebtheit: int = Field(nullable=False, default=0)
    bestand: int | None = Field() # sa_column_kwargs={"unsigned": True}


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
    lieferant: "Lieferant" = Relationship(back_populates="artikel")
    produktgruppe: "Produktgruppe" = Relationship(back_populates="artikel")
    pfand: Pfand = Relationship(back_populates="artikel")
    rabattaktion: list["Rabattaktion"] = Relationship(back_populates="artikel")


# For reading articles
class ArtikelPublic(ArtikelBase):
    artikel_id: int
    produktgruppen_id: int
    lieferant_id: int

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
    aktionsname: str = Field(max_length=50)
    rabatt_relativ: float | None = Field(sa_column=DECIMAL(precision=6, scale=5))
    rabatt_absolut: float | None = Field(sa_column=DECIMAL(precision=13, scale=2))
    mengenrabatt_schwelle: int | None = Field(default=None) # sa_column_kwargs={"unsigned": True}
    mengenrabatt_anzahl_kostenlos: int | None = Field(default=None) # sa_column_kwargs={"unsigned": True}
    mengenrabatt_relativ: float | None = Field(sa_column=DECIMAL(precision=6, scale=5))
    von: datetime = Field(nullable=False)
    bis: datetime | None = Field(nullable=True)


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