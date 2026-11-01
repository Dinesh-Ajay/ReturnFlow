import pytest
import os
from sqlalchemy.engine import make_url
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.config import settings

# Test code includes API calls and explicit commits, so always bind the whole
# application (not only the fixture session) to a separately named test DB.
test_database = make_url(settings.TEST_DATABASE_URL)
test_database_name = test_database.database or ""
if not (test_database_name.endswith("_test") or "_test_" in test_database_name):
    raise RuntimeError(
        "Refusing to run tests: TEST_DATABASE_URL must point to a dedicated database "
        "whose name ends in '_test' or contains '_test_'."
    )
settings.DATABASE_URL = settings.TEST_DATABASE_URL
settings.GROUND_TRUTH_DIR = os.getenv("RETURN_FLOW_TEST_GROUND_TRUTH_DIR", settings.GROUND_TRUTH_DIR)
if not settings.INITIAL_ADMIN_PASSWORD:
    settings.INITIAL_ADMIN_PASSWORD = "ReturnFlow-Test-Only-Password-2026!"
if not settings.AUTH_SECRET:
    settings.AUTH_SECRET = "ReturnFlow-Test-Only-Auth-Secret-2026!"
from app.database.base import Base
from app.database.session import get_db
from app.main import app

# Use existing MySQL connection or SQLite in-memory for fast testing
@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(settings.TEST_DATABASE_URL, pool_pre_ping=True)
    from app.models.id_sequence import IDSequence
    from app.models.user import User, PasswordResetOTP
    from app.models.deposit_ledger import DepositLedger
    from sqlalchemy import inspect, text
    Base.metadata.create_all(bind=engine, tables=[User.__table__, PasswordResetOTP.__table__, IDSequence.__table__])
    insp = inspect(engine)
    if "deposit_ledger" in insp.get_table_names():
        uqs = {u["name"] for u in insp.get_unique_constraints("deposit_ledger")}
        if "uq_deposit_reference" not in uqs:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE deposit_ledger ADD CONSTRAINT uq_deposit_reference UNIQUE (transaction_reference)"))
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
        from app.services.auth_service import AuthService
        from app.database.session import SessionLocal
        with SessionLocal() as db:
            user = AuthService.bootstrap_admin_user(db)
            user.password_hash = AuthService.hash_password(settings.INITIAL_ADMIN_PASSWORD)
            db.commit()
        response = client.post("/api/auth/login", json={"email": settings.INITIAL_ADMIN_EMAIL, "password": settings.INITIAL_ADMIN_PASSWORD})
        assert response.status_code == 200
        client.headers["Authorization"] = "Bearer " + response.json()["access_token"]
        yield client
