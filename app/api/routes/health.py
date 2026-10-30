from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database.session import get_db
from app.config import settings

router = APIRouter(tags=["Health"])

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    db_ok = False
    try:
        db.execute(text("SELECT 1;"))
        db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": "HEALTHY" if db_ok else "UNHEALTHY",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database_connected": db_ok,
        "environment": settings.ENVIRONMENT
    }
