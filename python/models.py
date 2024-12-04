from typing import Optional
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import DECIMAL, Column
from datetime import datetime


class Lieferant(SQLModel, table=True):
    __tablename__ = 'lieferant'

    lieferant_id: int = Field(primary_key=True)
    lieferant_name: str = Field(max_length=50, nullable=False)
    lieferant_kurzname: Optional[str] = Field(max_length=10)
    n_artikel: Optional[int] = Field() # sa_column_kwargs={"unsigned": True}
    aktiv: bool = Field(nullable=False, default=True)

    artikel: list["Artikel"] = Relationship(back_populates="lieferant")


class Mwst(SQLModel, table=True):
    __tablename__ = 'mwst'

    mwst_id: int = Field(primary_key=True)
    mwst_satz: float = Field(sa_column= Column(DECIMAL(precision=6, scale=5), nullable=True))
    dsfinvk_ust_schluessel: int = Field(nullable=False) # sa_column_kwargs={"unsigned": True}, 
    dsfinvk_ust_beschr: Optional[str] = Field(max_length=55)

    produktgruppe: list["Produktgruppe"] = Relationship(back_populates="mwst")


class Pfand(SQLModel, table=True):
    __tablename__ = 'pfand'

    pfand_id: int = Field(primary_key=True)
    artikel_id: int = Field(foreign_key="artikel.artikel_id") # sa_column_kwargs={"unsigned": True}, 

    artikel: "Artikel" = Relationship(back_populates="pfand")
    produktgruppe: list["Produktgruppe"] = Relationship(back_populates="pfand")


#######################
# Produktgruppe models
#######################

# The base model, shared by all
class ProduktgruppeBase(SQLModel):
    toplevel_id: int = Field(default=1) # sa_column_kwargs={"unsigned": True}, 
    sub_id: Optional[int] = Field() # sa_column_kwargs={"unsigned": True}
    subsub_id: Optional[int] = Field() # sa_column_kwargs={"unsigned": True}
    produktgruppen_name: str = Field(max_length=50, nullable=False)
    std_einheit: Optional[str] = Field(max_length=10)
    n_artikel: Optional[int] = Field() # sa_column_kwargs={"unsigned": True}
    n_artikel_rekursiv: Optional[int] = Field() # sa_column_kwargs={"unsigned": True}

# The table model
class Produktgruppe(ProduktgruppeBase, table=True):
    __tablename__ = 'produktgruppe'

    produktgruppen_id: int = Field(primary_key=True)
    mwst_id: Optional[int] = Field(foreign_key="mwst.mwst_id") # sa_column_kwargs={"unsigned": True}, 
    pfand_id: Optional[int] = Field(foreign_key="pfand.pfand_id") # sa_column_kwargs={"unsigned": True}, 

    aktiv: bool = Field(nullable=False, default=True)
    
    # relationships
    artikel: list["Artikel"] = Relationship(back_populates="produktgruppe")
    mwst: Mwst = Relationship(back_populates="produktgruppe")
    pfand: Pfand = Relationship(back_populates="produktgruppe")

# For reading product groups
class ProduktgruppePublic(ProduktgruppeBase):
    produktgruppen_id: int
    mwst_id: int
    pfand_id: int

    aktiv: bool


# For creating product groups
class ProduktgruppeCreate(ProduktgruppeBase):
    mwst_id: int | None = None
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
    n_artikel: int | None = None
    n_artikel_rekursiv: int | None = None


#################
# Artikel models
#################

# The base model, shared by all
class ArtikelBase(SQLModel):
    artikel_nr: str = Field(max_length=30, nullable=False)
    artikel_name: str = Field(max_length=180, nullable=False)
    kurzname: Optional[str] = Field(max_length=50)
    menge: Optional[float] = Field(sa_column=DECIMAL(precision=8, scale=5))
    einheit: Optional[str] = Field(max_length=10)
    barcode: Optional[str] = Field(max_length=30)
    herkunft: Optional[str] = Field(max_length=100)
    vpe: Optional[int] # sa_column_kwargs={"unsigned": True}
    setgroesse: int = Field(nullable=False, default=1) # sa_column_kwargs={"unsigned": True}, 
    vk_preis: Optional[float] = Field(sa_column=DECIMAL(precision=13, scale=2))
    empf_vk_preis: Optional[float] = Field(sa_column=DECIMAL(precision=13, scale=2))
    ek_rabatt: Optional[float] = Field(sa_column=DECIMAL(precision=6, scale=5))
    ek_preis: Optional[float] = Field(sa_column=DECIMAL(precision=13, scale=2))
    variabler_preis: bool = Field(nullable=False, default=False)
    sortiment: bool = Field(nullable=False, default=False)
    lieferbar: bool = Field(nullable=False, default=False)
    beliebtheit: int = Field(nullable=False, default=0)
    bestand: Optional[int] = Field() # sa_column_kwargs={"unsigned": True}

# The table model
class Artikel(ArtikelBase, table=True):
    __tablename__ = 'artikel'

    artikel_id: int | None = Field(default=None, primary_key=True)
    # id = Column(Integer, Sequence('user_id_seq', start=100, increment=1), primary_key=True)
    produktgruppen_id: int = Field(foreign_key="produktgruppe.produktgruppen_id", nullable=False, default=8)
    lieferant_id: int = Field(foreign_key="lieferant.lieferant_id", nullable=False, default=1)

    von: Optional[datetime] = Field(nullable=True, default=None)
    bis: Optional[datetime] = Field(nullable=True, default=None)
    aktiv: bool = Field(nullable=False, default=True)

    # relationships
    lieferant: "Lieferant" = Relationship(back_populates="artikel")
    produktgruppe: "Produktgruppe" = Relationship(back_populates="artikel")
    pfand: Pfand = Relationship(back_populates="artikel")


# For reading articles
class ArtikelPublic(ArtikelBase):
    artikel_id: int
    produktgruppen_id: int
    lieferant_id: int

    von: Optional[datetime] = Field()
    bis: Optional[datetime] = Field()
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