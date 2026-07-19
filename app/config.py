from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "JSJ6 Enterprise Portfolio Management")
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
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "http://localhost:8080")
    trust_proxy_hops: int = max(0, int(os.getenv("TRUST_PROXY_HOPS", "0")))
    rate_limit_requests: int = max(1, int(os.getenv("RATE_LIMIT_REQUESTS", "300")))
    rate_limit_window_seconds: int = max(1, int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "900")))


settings = Settings()

def _read_version() -> str:
    """Single source of truth for the release version (VERSION file at repo root)."""
    try:
        return (Path(__file__).resolve().parent.parent / "VERSION").read_text().strip()
    except OSError:
        return "0.8.0"


APP_VERSION = _read_version()
