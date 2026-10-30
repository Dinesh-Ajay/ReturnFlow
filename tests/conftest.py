import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.config import settings
from app.database.base import Base
from app.database.session import get_db
from app.main import app

# Use existing MySQL connection or SQLite in-memory for fast testing
@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    return engine

@pytest.fixture(scope="function")
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    SessionTest = sessionmaker(bind=connection)
    session = SessionTest()

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="module")
def api_client():
    with TestClient(app) as client:
        yield client
