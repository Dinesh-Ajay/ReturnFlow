import pytest
from app.services.auth_service import AuthService
from app.database.session import SessionLocal
from app.config import settings

def test_admin_bootstrap_and_login(api_client):
    db = SessionLocal()
    try:
        user = AuthService.bootstrap_admin_user(db)
        user.password_hash = AuthService.hash_password(settings.INITIAL_ADMIN_PASSWORD)
        db.commit()
        assert user.email == settings.INITIAL_ADMIN_EMAIL
        assert user.full_name == settings.INITIAL_ADMIN_NAME
        assert user.role == "Operations Manager"
    finally:
        db.close()

    # Test valid login
    res = api_client.post("/api/auth/login", json={
        "email": settings.INITIAL_ADMIN_EMAIL,
        "password": settings.INITIAL_ADMIN_PASSWORD
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == settings.INITIAL_ADMIN_EMAIL
    assert data["user"]["full_name"] == settings.INITIAL_ADMIN_NAME

    token = data["access_token"]

    # Test /api/auth/me
    res_me = api_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_me.status_code == 200
    assert res_me.json()["full_name"] == settings.INITIAL_ADMIN_NAME

def test_invalid_login_rejected(api_client):
    res = api_client.post("/api/auth/login", json={
        "email": settings.INITIAL_ADMIN_EMAIL,
        "password": "WrongPassword123!"
    })
    assert res.status_code == 401
    assert "Invalid email or password" in res.json()["detail"]

def test_password_recovery_workflow(api_client):
    db = SessionLocal()
    try:
        user = AuthService.bootstrap_admin_user(db)
        
        from app.models.user import PasswordResetOTP
        from datetime import datetime, timedelta, timezone
        import hashlib

        raw_otp = "123456"
        otp_hash = hashlib.sha256(raw_otp.encode()).hexdigest()
        record = PasswordResetOTP(
            email=user.email,
            otp_hash=otp_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            attempts=0,
            is_used=False
        )
        db.add(record)
        db.commit()
    finally:
        db.close()

    # 1. Test invalid OTP
    res_inv = api_client.post("/api/auth/verify-otp", json={
        "email": settings.INITIAL_ADMIN_EMAIL,
        "otp": "999999"
    })
    assert res_inv.status_code == 400
    assert "Invalid verification code" in res_inv.json()["detail"]

    # 2. Test valid OTP
    res_valid = api_client.post("/api/auth/verify-otp", json={
        "email": settings.INITIAL_ADMIN_EMAIL,
        "otp": "123456"
    })
    assert res_valid.status_code == 200
    reset_token = res_valid.json()["reset_token"]
    assert reset_token is not None

    # 3. Test password reset
    res_reset = api_client.post("/api/auth/reset-password", json={
        "email": settings.INITIAL_ADMIN_EMAIL,
        "reset_token": reset_token,
        "new_password": "NewSecretPassword2026!",
        "confirm_password": "NewSecretPassword2026!"
    })
    assert res_reset.status_code == 200
    assert "reset successfully" in res_reset.json()["message"]

    # 4. Log in with new password
    res_new_login = api_client.post("/api/auth/login", json={
        "email": settings.INITIAL_ADMIN_EMAIL,
        "password": "NewSecretPassword2026!"
    })
    assert res_new_login.status_code == 200
    assert "access_token" in res_new_login.json()

    # 5. Restore default admin password so development database user is preserved
    from app.models.user import User
    db_restore = SessionLocal()
    try:
        user_restore = db_restore.query(User).filter(User.email == settings.INITIAL_ADMIN_EMAIL).first()
        if user_restore:
            user_restore.password_hash = AuthService.hash_password(settings.INITIAL_ADMIN_PASSWORD)
            db_restore.commit()
    finally:
        db_restore.close()

def test_export_assets_csv(api_client):
    res = api_client.get("/api/exports/assets?format=csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["Content-Type"]
    assert "attachment; filename=" in res.headers["Content-Disposition"]
    assert "Asset ID,Serial Number" in res.text

def test_export_assets_pdf(api_client):
    res = api_client.get("/api/exports/assets?format=pdf")
    assert res.status_code == 200
    assert "application/pdf" in res.headers["Content-Type"]
    assert "attachment; filename=" in res.headers["Content-Disposition"]
    assert res.content.startswith(b"%PDF")

def test_export_assets_json(api_client):
    res = api_client.get("/api/exports/assets?format=json")
    assert res.status_code == 200
    assert "application/json" in res.headers["Content-Type"]
    assert "attachment; filename=" in res.headers["Content-Disposition"]
    assert "ReturnFlow Asset Registry" in res.text

def test_export_financial_and_inspections(api_client):
    res_fin = api_client.get("/api/exports/financial?format=csv")
    assert res_fin.status_code == 200
    assert "Entry ID" in res_fin.text

    res_insp = api_client.get("/api/exports/inspections?format=pdf")
    assert res_insp.status_code == 200
    assert res_insp.content.startswith(b"%PDF")
