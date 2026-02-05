import pytest
from sqlmodel import SQLModel, create_engine, Session

@pytest.fixture
def session():
    """
    Provides a fresh in-memory SQLite DB session for each test.
    """
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session