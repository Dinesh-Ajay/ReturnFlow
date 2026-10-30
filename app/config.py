import os
from datetime import date, datetime
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME: str = "ReturnFlow"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Database Settings
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "mysql+pymysql://root:root@localhost:3306/returnflow_db?charset=utf8mb4"
    )
    TEST_DATABASE_URL: str = os.getenv(
        "TEST_DATABASE_URL", 
        "mysql+pymysql://root:root@localhost:3306/returnflow_db?charset=utf8mb4"
    )
    
    # Supabase / PostgreSQL Support
    SUPABASE_URL: Optional[str] = os.getenv("SUPABASE_URL", None)
    SUPABASE_KEY: Optional[str] = os.getenv("SUPABASE_KEY", None)
    
    # Better Auth & Security
    AUTH_SECRET: str = os.getenv("AUTH_SECRET", "returnflow-secret-key-32-chars-minimum-prod")
    AUTH_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    
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
