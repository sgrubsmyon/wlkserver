import threading

from fastapi import Depends
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from typing import Annotated
from sqlmodel import Session, create_engine

from . import config


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
    key = "training" if config.training_mode() else "production"
    with _lock:
        if key not in _engines:
            _engines[key] = _make_engine(
                config.training_db_url() if key == "training" else config.database_url()
            )
        return _engines[key]


def get_production_engine() -> Engine:
    """The production engine, also from the training instance (user mirroring)."""
    with _lock:
        if "production" not in _engines:
            _engines["production"] = _make_engine(config.database_url())
        return _engines["production"]


def get_session():
    with Session(get_engine()) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
