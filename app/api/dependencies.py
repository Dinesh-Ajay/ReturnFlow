"""Fail-closed authentication and explicit, deliberately small role policy."""
from typing import Optional
from fastapi import Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.services.auth_service import AuthService
from app.models.user import User


def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": "Bearer"})
    payload = AuthService.decode_access_token(authorization[7:].strip())
    if not payload or not isinstance(payload.get("sub"), str):
        raise HTTPException(401, "Invalid or expired token")
    user = db.query(User).filter_by(email=payload["sub"], is_active=True).first()
    if not user:
        raise HTTPException(401, "Inactive or unknown user")
    return user


def authorize_business_request(request: Request, user: User = Depends(get_current_user)):
    # Roles are authoritative database values, never X-User-Role or JWT claims.
    readers = {"Operations Manager", "Operations Staff", "Finance Manager", "Viewer"}
    if user.role not in readers:
        raise HTTPException(403, "Role not permitted")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        allowed = {"Operations Manager"}
        if request.url.path.startswith("/api/deposits"):
            allowed.add("Finance Manager")
        elif not request.url.path.startswith("/api/validation"):
            allowed.add("Operations Staff")
        if user.role not in allowed:
            raise HTTPException(403, "Role cannot perform this operation")
    return user
