import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine, Session

@pytest.fixture
def session():
    """
    Provides a fresh in-memory SQLite DB session for each test.
    StaticPool + check_same_thread=False so that the DB can also be
    accessed from another thread (e.g. via FastAPI's TestClient).
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session