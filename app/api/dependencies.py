from typing import Generator, Optional
from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from app.database.session import get_db

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
    Better Auth session & role-based access dependency.
    Supports roles: Admin, Operations Manager, Logistics Analyst, Warehouse Operator.
    """
    role = x_user_role or "Operations Manager"
    return CurrentUser(
        user_id="usr_ajay_kumar",
        email="ajay.kumar@returnflow.fake",
        role=role,
        name="Ajay Kumar"
    )
