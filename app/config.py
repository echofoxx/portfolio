from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "DDC5I Enterprise Portfolio Management")
    environment: str = os.getenv("ENVIRONMENT", "development")
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://ddc5i:ddc5i@db:5432/ddc5i_portfolio"
    )
    secret_key: str = os.getenv("SECRET_KEY", "change-me-before-production")
    session_hours: int = int(os.getenv("SESSION_HOURS", "12"))
    upload_dir: str = os.getenv("UPLOAD_DIR", "/app/storage")
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "10"))
    app_port: int = int(os.getenv("APP_PORT", "8080"))
    demo_auth_enabled: bool = os.getenv("DEMO_AUTH_ENABLED", "true").lower() == "true"
    mailpit_url: str = os.getenv("MAILPIT_URL", "http://mailpit:8025")


settings = Settings()
