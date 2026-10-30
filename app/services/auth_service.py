import hmac
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User, PasswordResetOTP
from app.services.email_service import EmailService
from app.utils.logging_config import logger

class AuthService:
    """
    Handles authentication, password hashing, JWT sessions,
    and secure OTP password recovery workflows.
    """

    @staticmethod
    def hash_password(plain_password: str) -> str:
        """Securely hash a password using PBKDF2-HMAC-SHA256 with a random salt."""
        salt = secrets.token_hex(16)
        iterations = 100000
        key = hashlib.pbkdf2_hmac(
            'sha256',
            plain_password.encode('utf-8'),
            salt.encode('utf-8'),
            iterations
        )
        return f"pbkdf2:sha256:{iterations}${salt}${key.hex()}"

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify plain password against PBKDF2 hash using timing-safe comparison."""
        try:
            parts = hashed_password.split('$')
            if len(parts) != 3:
                return False
            algo_spec, salt, expected_hash = parts
            _, _, iterations_str = algo_spec.split(':')
            iterations = int(iterations_str)

            key = hashlib.pbkdf2_hmac(
                'sha256',
                plain_password.encode('utf-8'),
                salt.encode('utf-8'),
                iterations
            )
            return hmac.compare_digest(key.hex(), expected_hash)
        except Exception as e:
            logger.error(f"Error verifying password hash: {e}")
            return False

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create signed JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
        encoded_jwt = jwt.encode(to_encode, settings.AUTH_SECRET, algorithm=settings.AUTH_ALGORITHM)
        return encoded_jwt

    @staticmethod
    def decode_access_token(token: str) -> Optional[dict]:
        """Decode and validate a JWT access token."""
        try:
            payload = jwt.decode(token, settings.AUTH_SECRET, algorithms=[settings.AUTH_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            logger.debug("JWT token has expired.")
            return None
        except jwt.InvalidTokenError as e:
            logger.debug(f"Invalid JWT token: {e}")
            return None

    @classmethod
    def bootstrap_admin_user(cls, db: Session) -> User:
        """
        Ensures the Operations Manager account (Dinesh Ajay / dineshajay874@gmail.com)
        exists in the database without overwriting existing passwords or duplicating.
        """
        email_clean = settings.INITIAL_ADMIN_EMAIL.strip().lower()
        existing = db.query(User).filter(User.email == email_clean).first()
        if existing:
            return existing

        logger.info(f"Bootstrapping initial Operations Manager account: {email_clean}")
        admin_user = User(
            full_name=settings.INITIAL_ADMIN_NAME,
            email=email_clean,
            role=settings.INITIAL_ADMIN_ROLE,
            password_hash=cls.hash_password(settings.INITIAL_ADMIN_PASSWORD),
            is_active=True
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        logger.info(f"Successfully bootstrapped Operations Manager user_id={admin_user.user_id}")
        return admin_user

    @classmethod
    def authenticate(cls, db: Session, email: str, password: str) -> Optional[User]:
        """Authenticate user by email and password."""
        email_clean = email.strip().lower()
        user = db.query(User).filter(User.email == email_clean).first()
        if not user or not user.is_active:
            return None
        if not cls.verify_password(password, user.password_hash):
            return None
        return user

    @classmethod
    def request_password_reset_otp(cls, db: Session, email: str) -> Tuple[bool, str]:
        """
        Generates and emails a single-use 6-digit OTP for password reset.
        Enforces rate limiting cooldown and expiration controls.
        """
        email_clean = email.strip().lower()
        user = db.query(User).filter(User.email == email_clean, User.is_active == True).first()
        if not user:
            # Prevent account enumeration by returning a generic prompt, or clear status if internal
            return False, f"No active ReturnFlow account found for {email_clean}."

        now = datetime.now(timezone.utc)

        # Check rate limiting cooldown (e.g., 60 seconds)
        recent_otp = db.query(PasswordResetOTP).filter(
            PasswordResetOTP.email == email_clean
        ).order_by(PasswordResetOTP.created_at.desc()).first()

        if recent_otp:
            # Handle naive or aware datetimes cleanly
            recent_time = recent_otp.created_at
            if recent_time.tzinfo is None:
                recent_time = recent_time.replace(tzinfo=timezone.utc)
            elapsed = (now - recent_time).total_seconds()
            if elapsed < settings.OTP_RESEND_COOLDOWN_SECONDS:
                remaining = int(settings.OTP_RESEND_COOLDOWN_SECONDS - elapsed)
                return False, f"Please wait {remaining} seconds before requesting a new verification code."

        # Generate secure random 6-digit code
        raw_otp = f"{secrets.randbelow(900000) + 100000:06d}"
        otp_hash = hashlib.sha256(raw_otp.encode('utf-8')).hexdigest()
        expires_at = now + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

        otp_record = PasswordResetOTP(
            email=email_clean,
            otp_hash=otp_hash,
            attempts=0,
            expires_at=expires_at,
            is_used=False
        )
        db.add(otp_record)
        db.commit()

        # Send via Gmail SMTP
        success, send_msg = EmailService.send_otp_email(
            to_email=user.email,
            recipient_name=user.full_name,
            otp_code=raw_otp
        )

        if not success:
            return False, send_msg

        return True, f"A 6-digit verification code has been sent to {user.email}."

    @classmethod
    def verify_otp(cls, db: Session, email: str, otp_code: str) -> Tuple[bool, str, Optional[str]]:
        """
        Verifies the 6-digit OTP. Returns (success, message, reset_token).
        """
        email_clean = email.strip().lower()
        code_clean = otp_code.strip()
        now = datetime.now(timezone.utc)

        record = db.query(PasswordResetOTP).filter(
            PasswordResetOTP.email == email_clean,
            PasswordResetOTP.is_used == False
        ).order_by(PasswordResetOTP.created_at.desc()).first()

        if not record:
            return False, "No active verification code found. Please request a new code.", None

        rec_exp = record.expires_at
        if rec_exp.tzinfo is None:
            rec_exp = rec_exp.replace(tzinfo=timezone.utc)

        if now > rec_exp:
            record.is_used = True
            db.commit()
            return False, "The verification code has expired (5 minute SLA). Please request a new code.", None

        if record.attempts >= settings.OTP_MAX_ATTEMPTS:
            record.is_used = True
            db.commit()
            return False, "Maximum verification attempts exceeded. Please request a new code.", None

        record.attempts += 1
        submitted_hash = hashlib.sha256(code_clean.encode('utf-8')).hexdigest()

        if not hmac.compare_digest(record.otp_hash, submitted_hash):
            remaining = settings.OTP_MAX_ATTEMPTS - record.attempts
            db.commit()
            return False, f"Invalid verification code. {remaining} attempt(s) remaining.", None

        # OTP verified! Mark used and generate password reset token
        reset_token = secrets.token_urlsafe(32)
        record.reset_token = reset_token
        record.is_used = True
        db.commit()

        return True, "Code verified successfully.", reset_token

    @classmethod
    def reset_password(cls, db: Session, email: str, reset_token: str, new_password: str) -> Tuple[bool, str]:
        """
        Sets a new password using the validated reset token.
        """
        email_clean = email.strip().lower()
        if len(new_password) < 6:
            return False, "Password must be at least 6 characters long."

        record = db.query(PasswordResetOTP).filter(
            PasswordResetOTP.email == email_clean,
            PasswordResetOTP.reset_token == reset_token
        ).first()

        if not record:
            return False, "Invalid or expired password reset session. Please restart recovery."

        user = db.query(User).filter(User.email == email_clean, User.is_active == True).first()
        if not user:
            return False, "User account not found."

        user.password_hash = cls.hash_password(new_password)
        record.reset_token = None  # Consume token
        db.commit()

        logger.info(f"Password successfully reset for user {user.email}")
        return True, "Your password has been reset successfully. You can now log in."
