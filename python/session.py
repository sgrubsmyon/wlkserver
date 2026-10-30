import os
import threading

from dotenv import load_dotenv
from fastapi import Depends
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from typing import Annotated
from sqlmodel import Session, create_engine

load_dotenv()  # take environment variables from .env file

TRAINING_VALUES = ("1", "true", "yes", "on")


def is_training_mode() -> bool:
    """True when this API instance runs against the disposable training database."""
    return os.getenv("TRAINING_MODE", "").strip().lower() in TRAINING_VALUES


def _production_url() -> str:
    dbhost = os.getenv("DBHOST")
    dbname = os.getenv("DBNAME")
    dbuser = os.getenv("DBUSER")
    dbpass = os.getenv("DBPASS")
    # engine = create_engine("mysql+pymysql://<user>:<password>@<host>/<dbname>?charset=utf8mb4")
    # engine = create_engine("mariadb+mariadbconnector://<user>:<password>@<host>[:<port>]/<dbname>")
    return f"mariadb+mariadbconnector://{dbuser}:{dbpass}@{dbhost}/{dbname}"


def _training_url() -> str:
    url = os.getenv("TRAINING_DB_URL")
    if not url:
        raise RuntimeError(
            "TRAINING_MODE is enabled but TRAINING_DB_URL is not set "
            "(e.g. sqlite:///training.db or a separate MariaDB database)"
        )
    return url


def set_session_timezone(dbapi_connection, connection_record):
    """Set DB session to UTC so TIMESTAMP columns round-trip correctly."""
    cursor = dbapi_connection.cursor()
    cursor.execute("SET time_zone = '+00:00'")
    cursor.close()


def _make_engine(url: str) -> Engine:
    options = {}
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
        if url in ("sqlite://", "sqlite:///:memory:"):
            options["poolclass"] = StaticPool
    engine = create_engine(url, **options)
    if not url.startswith("sqlite"):
        event.listen(engine, "connect", set_session_timezone)
    return engine


# Engines are created lazily so tests can replace them and so a training-only
# deployment does not touch the production database until it mirrors the users.
_engines: dict[str, Engine] = {}
_lock = threading.Lock()


def get_engine() -> Engine:
    """Engine of the active mode (training sandbox when TRAINING_MODE is set)."""
    key = "training" if is_training_mode() else "production"
    with _lock:
        if key not in _engines:
            _engines[key] = _make_engine(
                _training_url() if key == "training" else _production_url()
            )
        return _engines[key]


def get_production_engine() -> Engine:
    """The production engine, also from the training instance (user mirroring)."""
    with _lock:
        if "production" not in _engines:
            _engines["production"] = _make_engine(_production_url())
        return _engines["production"]


def get_session():
    with Session(get_engine()) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
