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


class Produktgruppe(SQLModel, table=True):
    __tablename__ = 'produktgruppe'

    produktgruppen_id: int = Field(primary_key=True)
    toplevel_id: int = Field(default=1) # sa_column_kwargs={"unsigned": True}, 
    sub_id: Optional[int] = Field() # sa_column_kwargs={"unsigned": True}
    subsub_id: Optional[int] = Field() # sa_column_kwargs={"unsigned": True}
    produktgruppen_name: str = Field(max_length=50, nullable=False)
    mwst_id: Optional[int] = Field(foreign_key="mwst.mwst_id") # sa_column_kwargs={"unsigned": True}, 
    pfand_id: Optional[int] = Field(foreign_key="pfand.pfand_id") # sa_column_kwargs={"unsigned": True}, 
    std_einheit: Optional[str] = Field(max_length=10)
    n_artikel: Optional[int] = Field() # sa_column_kwargs={"unsigned": True}
    n_artikel_rekursiv: Optional[int] = Field() # sa_column_kwargs={"unsigned": True}
    aktiv: bool = Field(nullable=False, default=True)

    artikel: list["Artikel"] = Relationship(back_populates="produktgruppe")
    mwst: Mwst = Relationship(back_populates="produktgruppe")
    pfand: Pfand = Relationship(back_populates="produktgruppe")


class Artikel(SQLModel, table=True):
    __tablename__ = 'artikel'

    artikel_id: int = Field(primary_key=True)
    # id = Column(Integer, Sequence('user_id_seq', start=100, increment=1), primary_key=True)
    produktgruppen_id: int = Field(foreign_key="produktgruppe.produktgruppen_id", nullable=False, default=8)
    lieferant_id: int = Field(foreign_key="lieferant.lieferant_id", nullable=False, default=1)
    artikel_nr: str = Field(max_length=30, nullable=False)
    artikel_name: str = Field(max_length=180, nullable=False)
    kurzname: Optional[str] = Field(max_length=50)
    menge: Optional[float] = Field(sa_column=DECIMAL(precision=8, scale=5))
    einheit: Optional[str] = Field(max_length=10)
    barcode: Optional[str] = Field(max_length=30)
    herkunft: Optional[str] = Field(max_length=100)
    vpe: Optional[int] = Field() # sa_column_kwargs={"unsigned": True}
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
    von: Optional[datetime] = Field()
    bis: Optional[datetime] = Field()
    aktiv: bool = Field(nullable=False, default=True)

    # relationships
    lieferant: "Lieferant" = Relationship(back_populates="artikel")
    produktgruppe: "Produktgruppe" = Relationship(back_populates="artikel")
    pfand: Pfand = Relationship(back_populates="artikel")

