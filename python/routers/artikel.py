from dotenv import load_dotenv
import os

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, Relationship, create_engine, select

# from ..dependencies import get_token_header

from ..models import Artikel

load_dotenv()  # take environment variables from .env file


dbhost = os.getenv("DBHOST")
dbname = os.getenv("DBNAME")
dbuser = os.getenv("DBUSER")
dbpass = os.getenv("DBPASS")
# engine = create_engine("mysql+pymysql://<user>:<password>@<host>/<dbname>?charset=utf8mb4")
# engine = create_engine("mariadb+mariadbconnector://<user>:<password>@<host>[:<port>]/<dbname>")
engine = create_engine(f"mariadb+mariadbconnector://{dbuser}:{dbpass}@{dbhost}/{dbname}")
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
def read_artikel(
    session: SessionDep, aktiv_only: bool = True,
    search_string: str = "", barcode: str = "", artikel_nr: str = "", artikel_name: str = "",
    offset: int = 0, limit: Annotated[int, Query(le=100)] = 100
    ) -> list[Artikel]:
    selection = select(Artikel)
    if aktiv_only:
        selection = selection.where(Artikel.aktiv == True)
    if search_string:
        # Split the search string into space separated terms
        search_terms = search_string.split()
        # Each search term must be present in one of the searchable columns
        for (term) in search_terms:
            selection = selection.where(
                Artikel.artikel_name.contains(term) |
                Artikel.kurzname.contains(term) |
                Artikel.artikel_nr.contains(term) |
                Artikel.herkunft.contains(term) |
                Artikel.barcode.contains(term)
            )
    elif barcode:
        selection = selection.where(Artikel.barcode == barcode)
    elif artikel_nr:
        selection = selection.where(Artikel.artikel_nr.contains(artikel_nr))
    elif artikel_name:
        selection = selection.where(Artikel.artikel_name.contains(artikel_name) | Artikel.kurzname.contains(artikel_name))
    artikel = session.exec(
        selection.offset(offset).limit(limit)
            .order_by(Artikel.artikel_name, Artikel.lieferant_id)).all()
    return artikel


@router.get("/{artikel_id}")
def read_single_artikle(artikel_id: int, session: SessionDep) -> Artikel:
    artikel = session.get(Artikel, artikel_id)
    if not artikel:
        raise HTTPException(status_code=404, detail="Artikel not found")
    return artikel


@router.post("/")
def create_artikel(artikel: Artikel, session: SessionDep) -> Artikel:
    session.add(artikel)
    session.commit()
    session.refresh(artikel)
    return artikel


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