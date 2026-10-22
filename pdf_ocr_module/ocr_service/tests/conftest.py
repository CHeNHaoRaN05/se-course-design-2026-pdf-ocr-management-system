from datetime import datetime, timedelta, timezone
import secrets
from types import SimpleNamespace

from fastapi.testclient import TestClient
import jwt
import pytest

from ocr_service.api import create_app
from ocr_service.config import Settings
from ocr_service.db import Base


def authorization(settings, subject="lab-member", role="user"):
    issued = datetime.now(timezone.utc)
    claims = {"sub": subject, "role": role, "iss": settings.jwt_issuer, "aud": settings.jwt_audience,
              "iat": issued, "exp": issued + timedelta(minutes=20)}
    return {"Authorization": "Bearer " + jwt.encode(claims, settings.jwt_secret, algorithm="HS256")}


@pytest.fixture
def service(tmp_path):
    settings = Settings(database_url="sqlite:///" + (tmp_path / "inventory.sqlite3").as_posix(),
                        storage=tmp_path, jwt_secret=secrets.token_hex(32),
                        max_attempts=2, retry_delay_seconds=0,
                        custom_recognizer=None, handwriting_detector=None)
    app = create_app(settings)
    Base.metadata.create_all(app.state.ocr_engine)
    with TestClient(app, headers=authorization(settings)) as client:
        yield SimpleNamespace(config=settings, app=app, client=client, sessions=app.state.ocr_sessions)
