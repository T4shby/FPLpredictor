from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.core.settings import get_settings
from backend.app.main import app


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_status_endpoint_without_data():
    get_settings.cache_clear()
    client = TestClient(app)
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    body = response.json()
    assert "model_version" in body
    assert body["timezone"] == "Europe/London"


def test_admin_refresh_requires_token():
    client = TestClient(app)
    response = client.post("/api/v1/admin/refresh")
    assert response.status_code == 401
