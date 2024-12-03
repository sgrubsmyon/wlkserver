import os
from dotenv import load_dotenv
from fastapi import Depends
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


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]