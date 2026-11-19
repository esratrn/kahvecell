import os
import tempfile
from pathlib import Path

# Uygulama import edilmeden önce ayarlanmalı: testler asıl kahvecell.db'ye dokunmaz.
_TEST_DB = Path(tempfile.gettempdir()) / "kahvecell_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB.as_posix()}"
os.environ["ENVIRONMENT"] = "development"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app import models  # noqa: E402, F401
from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from seed.seed_data import seed_plans  # noqa: E402


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
    # Uygulama açılışı migration'ları baştan uygular.
    with TestClient(app) as test_client:
        with SessionLocal.begin() as db:
            seed_plans(db)
        yield test_client


def login(client: TestClient, phone: str = "0555 111 22 33") -> dict:
    client.post("/api/v1/auth/register", json={"phone_number": phone})
    response = client.post(
        "/api/v1/auth/verify-otp", json={"phone_number": phone, "otp_code": "1234"}
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def auth_header(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}
