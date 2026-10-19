import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine, Session, select

from python.models import User
from python.utils.auth import hash_password


@pytest.fixture
def session():
    """
    Provides a fresh in-memory SQLite DB session for each test.
    StaticPool + check_same_thread=False so that the DB can also be
    accessed from another thread (e.g. via FastAPI's TestClient).
    Seeds a default test user (username 'test', password 'test',
    role 'mitarbeiter') for authenticated endpoints.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        if not session.exec(select(User).where(User.username == "test")).first():
            u = User(username="test", password_hash=hash_password("test"), role="mitarbeiter", active=True)
            u.user_id = None
            session.add(u)
            session.commit()
        yield session