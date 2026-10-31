from typing import Generator, Optional
from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.config import settings
from app.services.auth_service import AuthService

class CurrentUser:
    def __init__(self, user_id: str, email: str, role: str, name: str):
        self.user_id = user_id
        self.email = email
        self.role = role
        self.name = name

def get_current_user(
    authorization: Optional[str] = Header(None),
    x_user_role: Optional[str] = Header(None)
) -> CurrentUser:
    """
    Session & role-based access dependency.
    Supports JWT tokens from Authorization: Bearer <token>,
    falling back to the configured initial Operations Manager identity.
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
        payload = AuthService.decode_access_token(token)
        if payload:
            email_val = payload.get("email") or payload.get("sub") or settings.INITIAL_ADMIN_EMAIL
            return CurrentUser(
                user_id=str(payload.get("user_id", "usr_dinesh_ajay")),
                email=str(email_val),
                role=str(payload.get("role", settings.INITIAL_ADMIN_ROLE)),
                name=str(payload.get("name", settings.INITIAL_ADMIN_NAME))
            )

    role = x_user_role or settings.INITIAL_ADMIN_ROLE
    return CurrentUser(
        user_id="usr_dinesh_ajay",
        email=settings.INITIAL_ADMIN_EMAIL,
        role=role,
        name=settings.INITIAL_ADMIN_NAME
    )
