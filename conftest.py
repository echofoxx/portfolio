from __future__ import annotations

import os
from pathlib import Path

TEST_DB = Path(__file__).resolve().parent / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["UPLOAD_DIR"] = str(Path(__file__).resolve().parent / "uploads")
os.environ["ENVIRONMENT"] = "test"
os.environ["RATE_LIMIT_REQUESTS"] = "10000"
os.environ["RATE_LIMIT_WINDOW_SECONDS"] = "60"
os.environ["TRUST_PROXY_HOPS"] = "0"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.seed import seed_database


@pytest.fixture(scope="session", autouse=True)
def database():
    TEST_DB.unlink(missing_ok=True)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_database(db)
    yield
    Base.metadata.drop_all(bind=engine)
    TEST_DB.unlink(missing_ok=True)


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, username: str = "admin") -> None:
    response = client.post(
        "/login",
        data={"username": username, "password": "Demo123!", "next": "/dashboard"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Portfolio Overview" in response.text
