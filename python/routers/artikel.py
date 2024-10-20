from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Field, Session, SQLModel, Relationship, create_engine, select

# from ..dependencies import get_token_header

class Lieferant(SQLModel, table=True):
    __tablename__ = 'lieferant'

    lieferant_id: int = Field(sa_column_kwargs={"auto_increment": True}, primary_key=True)
    lieferant_name: str = Field(max_length=50, nullable=False)
    lieferant_kurzname: Optional[str] = Field(max_length=10)
    n_artikel: Optional[int] = Field(sa_column_kwargs={"unsigned": True})
    aktiv: bool = Field(nullable=False, default=True)

    artikel: list["Artikel"] = Relationship(back_populates="lieferant")


class Mwst(SQLModel, table=True):
    __tablename__ = 'mwst'

    mwst_id: int = Field(sa_column_kwargs={"auto_increment": True}, primary_key=True)
    mwst_satz: float = Field(sa_column_kwargs={"precision": 6, "scale": 5}, nullable=False)
    dsfinvk_ust_schluessel: int = Field(sa_column_kwargs={"unsigned": True}, nullable=False)
    dsfinvk_ust_beschr: Optional[str] = Field(max_length=55)

    produktgruppe: list["Produktgruppe"] = Relationship(back_populates="mwst")


class Pfand(SQLModel, table=True):
    __tablename__ = 'pfand'

    pfand_id: int = Field(sa_column_kwargs={"auto_increment": True}, primary_key=True)
    artikel_id: int = Field(sa_column_kwargs={"unsigned": True}, foreign_key="artikel.artikel_id")

    artikel: "Artikel" = Relationship(back_populates="pfand")
    produktgruppe: list["Produktgruppe"] = Relationship(back_populates="pfand")

class Produktgruppe(SQLModel, table=True):
    __tablename__ = 'produktgruppe'

    produktgruppen_id: int = Field(sa_column_kwargs={"auto_increment": True}, primary_key=True)
    toplevel_id: int = Field(sa_column_kwargs={"unsigned": True}, default=1)
    sub_id: Optional[int] = Field(sa_column_kwargs={"unsigned": True})
    subsub_id: Optional[int] = Field(sa_column_kwargs={"unsigned": True})
    produktgruppen_name: str = Field(max_length=50, nullable=False)
    mwst_id: Optional[int] = Field(sa_column_kwargs={"unsigned": True}, foreign_key="mwst.mwst_id")
    pfand_id: Optional[int] = Field(sa_column_kwargs={"unsigned": True}, foreign_key="pfand.pfand_id")
    std_einheit: Optional[str] = Field(max_length=10)
    n_artikel: Optional[int] = Field(sa_column_kwargs={"unsigned": True})
    n_artikel_rekursiv: Optional[int] = Field(sa_column_kwargs={"unsigned": True})
    aktiv: bool = Field(nullable=False, default=True)

    artikel: list["Artikel"] = Relationship(back_populates="produktgruppe")
    mwst: Mwst = Relationship(back_populates="produktgruppe")
    pfand: Pfand = Relationship(back_populates="produktgruppe")

class Artikel(SQLModel, table=True):
    __tablename__ = 'artikel'

    artikel_id: int = Field(primary_key=True, sa_column_kwargs={"auto_increment": True})
    produktgruppen_id: int = Field(foreign_key="produktgruppe.produktgruppen_id")
    lieferant_id: int = Field(foreign_key="lieferant.lieferant_id")
    artikel_nr: str = Field(max_length=30, nullable=False)
    artikel_name: str = Field(max_length=180, nullable=False)
    kurzname: Optional[str] = Field(max_length=50)
    menge: Optional[float] = Field(sa_column_kwargs={"precision": 8, "scale": 5})
    einheit: Optional[str] = Field(max_length=10)
    barcode: Optional[str] = Field(max_length=30)
    herkunft: Optional[str] = Field(max_length=100)
    vpe: Optional[int] = Field(sa_column_kwargs={"unsigned": True})
    setgroesse: int = Field(sa_column_kwargs={"unsigned": True}, nullable=False, default=1)
    vk_preis: Optional[float] = Field(sa_column_kwargs={"precision": 13, "scale": 2})
    empf_vk_preis: Optional[float] = Field(sa_column_kwargs={"precision": 13, "scale": 2})
    ek_rabatt: Optional[float] = Field(sa_column_kwargs={"precision": 6, "scale": 5})
    ek_preis: Optional[float] = Field(sa_column_kwargs={"precision": 13, "scale": 2})
    variabler_preis: bool = Field(nullable=False, default=False)
    sortiment: bool = Field(nullable=False, default=False)
    lieferbar: bool = Field(nullable=False, default=False)
    beliebtheit: int = Field(nullable=False, default=0)
    bestand: Optional[int] = Field(sa_column_kwargs={"unsigned": True})
    von: Optional[str] = Field(sa_column_kwargs={"type": "datetime"})
    bis: Optional[str] = Field(sa_column_kwargs={"type": "datetime"})
    aktiv: bool = Field(nullable=False, default=True)

    # relationships
    lieferant: "Lieferant" = Relationship(back_populates="artikel")
    produktgruppe: "Produktgruppe" = Relationship(back_populates="artikel")
    pfand: Pfand = Relationship(back_populates="artikel")


# engine = create_engine("mysql+pymysql://mitarbeiter:p@localhost/kasse?charset=utf8mb4")
# engine = create_engine("mariadb+mariadbconnector://<user>:<password>@<host>[:<port>]/<dbname>")
engine = create_engine("mariadb+mariadbconnector://mitarbeiter:p@localhost/kasse")
print("engine: ")
print(engine)

# fake_artikel_db = {"cr01": {"bezeichnung": "Costa Rica Cola"}, "ros": {"bezeichnung": "Rosinen"}}


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]

router = APIRouter(
    prefix="/artikel",
    tags=["artikel"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
async def read_artikel():
    return fake_artikel_db


@router.get("/{artikel_id}")
async def read_single_artikel(artikel_id: str):
    if artikel_id not in fake_artikel_db:
        raise HTTPException(status_code=404, detail="Artikel not found")
    return {"bezeichnung": fake_artikel_db[artikel_id]["bezeichnung"], "artikel_id": artikel_id}


@router.put(
    "/{artikel_id}",
    tags=["artikel"],
    responses={403: {"description": "Operation forbidden"}},
)
async def update_artikel(artikel_id: str):
    if artikel_id != "cr01":
        raise HTTPException(
            status_code=403, detail="You can only update the artikel: cr01"
        )
    return {"artikel_id": artikel_id, "name": "The great Costa Rica Cola"}