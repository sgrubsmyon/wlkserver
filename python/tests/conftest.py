import os

import pytest
from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine, Session, select

from python.models import Lieferant, Produktgruppe, User
from python.session import set_session_timezone
from python.utils.auth import hash_password

# Optional MariaDB test database, reset before every test. Without it the suite
# uses a fresh in-memory SQLite database per test.
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


def _sqlite_engine():
    """Fresh in-memory SQLite DB; StaticPool + check_same_thread=False so the DB
    can also be accessed from another thread (e.g. via FastAPI's TestClient)."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


_engine = None


def _mariadb_engine():
    global _engine
    if _engine is None:
        name = make_url(TEST_DATABASE_URL).database or ""
        if "test" not in name.lower():
            raise RuntimeError(
                f"TEST_DATABASE_URL must point at a dedicated test database, got {name!r}"
            )
        _engine = create_engine(TEST_DATABASE_URL)
        event.listen(_engine, "connect", set_session_timezone)
        # checkfirst: an existing schema from generateDB.sql keeps its real DDL
        SQLModel.metadata.create_all(_engine, checkfirst=True)
    return _engine


def _reset(engine):
    """Empty every table, like the fresh in-memory DB the SQLite path gets."""
    with engine.connect() as conn:
        conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS=0")
        try:
            for table in SQLModel.metadata.sorted_tables:
                conn.exec_driver_sql(f"TRUNCATE TABLE `{table.name}`")
        finally:
            conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS=1")


@pytest.fixture
def session():
    """DB session, seeding the default test user (username 'test', password
    'test', role 'mitarbeiter') for authenticated endpoints."""
    if TEST_DATABASE_URL:
        engine = _mariadb_engine()
        _reset(engine)
    else:
        engine = _sqlite_engine()
    with Session(engine) as session:
        if not session.exec(select(User).where(User.username == "test")).first():
            u = User(username="test", password_hash=hash_password("test"), role="mitarbeiter", active=True)
            u.user_id = None
            session.add(u)
            session.commit()
        yield session


@pytest.fixture
def mariadb_engine():
    """The MariaDB test engine; the test is skipped without `TEST_DATABASE_URL`.

    Use it for tests that need several independent sessions/connections, which
    the single `session` fixture cannot provide.
    """
    if not TEST_DATABASE_URL:
        pytest.skip("requires TEST_DATABASE_URL (see deployment/create_test_db.sh)")
    return _mariadb_engine()


@pytest.fixture
def master_data(session):
    """The rows the model defaults rely on: `lieferant_id=1`, `produktgruppen_id=8`."""
    session.add(Lieferant(lieferant_id=1, lieferant_name="unbekannt"))
    session.add(Produktgruppe(produktgruppen_id=8, produktgruppen_name="Pfand optional"))
    session.commit()
    return session
