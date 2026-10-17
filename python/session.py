import os
from dotenv import load_dotenv
from fastapi import Depends
from sqlalchemy import event
from typing import Annotated
from sqlmodel import Session, create_engine

load_dotenv()  # take environment variables from .env file

dbhost = os.getenv("DBHOST")
dbname = os.getenv("DBNAME")
dbuser = os.getenv("DBUSER")
dbpass = os.getenv("DBPASS")
# engine = create_engine("mysql+pymysql://<user>:<password>@<host>/<dbname>?charset=utf8mb4")
# engine = create_engine("mariadb+mariadbconnector://<user>:<password>@<host>[:<port>]/<dbname>")
engine = create_engine(f"mariadb+mariadbconnector://{dbuser}:{dbpass}@{dbhost}/{dbname}")


@event.listens_for(engine, "connect")
def set_session_timezone(dbapi_connection, connection_record):
    """Set DB session to UTC so TIMESTAMP columns round-trip correctly."""
    cursor = dbapi_connection.cursor()
    cursor.execute("SET time_zone = '+00:00'")
    cursor.close()


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]