from sqlalchemy import create_engine, text
from app.config import settings

def get_engine(database_url: str = settings.DATABASE_URL):
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        return create_engine(database_url, connect_args=connect_args)
    else:
        return create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=15,
            max_overflow=25
        )

engine = get_engine()

def check_db_connection() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            return True
    except Exception:
        return False
