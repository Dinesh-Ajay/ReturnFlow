from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.auth_service import AuthService
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
    email: str
    password: str
    remember_me: Optional[bool] = False

class ForgotPasswordRequest(BaseModel):
    email: str

class VerifyOTPRequest(BaseModel):
    email: str
    otp: str

class ResetPasswordRequest(BaseModel):
    email: str
    reset_token: str
    new_password: str
    confirm_password: str

def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> Optional[User]:
    """Dependency to extract authenticated User from Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ")[1]
    payload = AuthService.decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    user = db.query(User).filter(User.email == payload["sub"], User.is_active == True).first()
    return user

@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user with email and password."""
    user = AuthService.authenticate(db, payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please verify your credentials."
        )

    token = AuthService.create_access_token(
        data={"sub": user.email, "role": user.role, "name": user.full_name}
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "user_id": user.user_id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role
        }
    }

@router.get("/me")
def get_current_user_profile(user: Optional[User] = Depends(get_current_user)):
    """Returns currently authenticated user profile."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated or session expired."
        )
    return {
        "user_id": user.user_id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role
    }

@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Initiates password reset by generating and emailing a 6-digit OTP."""
    success, message = AuthService.request_password_reset_otp(db, payload.email)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    return {"success": True, "message": message}

@router.post("/verify-otp")
def verify_otp(payload: VerifyOTPRequest, db: Session = Depends(get_db)):
    """Validates the 6-digit OTP and returns a single-use reset token."""
    success, message, reset_token = AuthService.verify_otp(db, payload.email, payload.otp)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    return {
        "success": True,
        "message": message,
        "reset_token": reset_token
    }

@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Updates password using verified reset token."""
    if payload.new_password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match. Please re-enter both passwords identically."
        )

    success, message = AuthService.reset_password(
        db, payload.email, payload.reset_token, payload.new_password
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    return {"success": True, "message": message}

@router.post("/logout")
def logout():
    """Invalidates client session."""
    return {"success": True, "message": "Successfully logged out."}
