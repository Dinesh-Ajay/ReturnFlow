import os
from datetime import date, datetime
from typing import Optional
from dotenv import load_dotenv
from sqlalchemy.engine import make_url

load_dotenv()


class Settings:
    APP_NAME: str = "ReturnFlow"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Database Settings
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "mysql+pymysql://returnflow_user:configure-me@localhost:3306/returnflow_db?charset=utf8mb4"
    )
    TEST_DATABASE_URL: str = os.getenv(
        "TEST_DATABASE_URL",
        make_url(DATABASE_URL).set(database=f"{make_url(DATABASE_URL).database or 'returnflow'}_test").render_as_string(hide_password=False)
    )
    
    # Supabase / PostgreSQL Support
    SUPABASE_URL: Optional[str] = os.getenv("SUPABASE_URL", None)
    SUPABASE_KEY: Optional[str] = os.getenv("SUPABASE_KEY", None)
    
    # Better Auth & Security
    AUTH_SECRET: str = os.getenv("AUTH_SECRET") or "returnflow-secret-key-32-chars-minimum-prod"
    AUTH_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    
    # Initial Operations Manager Account Bootstrap
    INITIAL_ADMIN_EMAIL: str = os.getenv("INITIAL_ADMIN_EMAIL", "dineshajay874@gmail.com")
    INITIAL_ADMIN_NAME: str = os.getenv("INITIAL_ADMIN_NAME", "Dinesh Ajay")
    INITIAL_ADMIN_ROLE: str = os.getenv("INITIAL_ADMIN_ROLE", "Operations Manager")
    INITIAL_ADMIN_PASSWORD: str = os.getenv("INITIAL_ADMIN_PASSWORD", "ReturnFlow@2026!")

    # SMTP Configuration (Gmail TLS)
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_EMAIL: str = os.getenv("SMTP_EMAIL", "dineshajay874@gmail.com")
    SMTP_APP_PASSWORD: str = os.getenv("SMTP_APP_PASSWORD", "")

    # OTP Security Controls
    OTP_EXPIRE_MINUTES: int = int(os.getenv("OTP_EXPIRE_MINUTES", "5"))
    OTP_MAX_ATTEMPTS: int = int(os.getenv("OTP_MAX_ATTEMPTS", "3"))
    OTP_RESEND_COOLDOWN_SECONDS: int = int(os.getenv("OTP_RESEND_COOLDOWN_SECONDS", "60"))

    # Google Analytics
    GA_MEASUREMENT_ID: Optional[str] = os.getenv("GA_MEASUREMENT_ID", "G-RETURNFLOW01")
    
    # Data Generation Settings
    RANDOM_SEED: int = int(os.getenv("RANDOM_SEED", "20261022"))
    REFERENCE_DATE: date = date(2026, 10, 22)
    DATA_PROFILE: str = os.getenv("DATA_PROFILE", "starter")
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "1000"))
    
    # API Settings
    API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    
    # Directories
    BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    GENERATED_DIR: str = os.path.join(DATA_DIR, "generated")
    GROUND_TRUTH_DIR: str = os.path.join(DATA_DIR, "ground_truth")
    EXPORTS_DIR: str = os.path.join(DATA_DIR, "exports")


settings = Settings()
