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


def test_html_dashboard_without_data():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert b"Squad" in response.content
    assert b"Starting XI" in response.content or b"No squad yet" in response.content
    assert response.headers.get("cache-control") == "no-store"


def test_html_dashboard_model_query():
    client = TestClient(app)
    response = client.get("/?model=D")
    assert response.status_code == 200
    assert b"Full" in response.content


def test_html_league_model_tab_shows_one_squad():
    client = TestClient(app)
    response = client.get("/league?model=B")
    assert response.status_code == 200
    assert b"/league?model=A" in response.content
    assert b"/league?model=B" in response.content
    assert response.content.count(b"<h2>") <= 1


def test_picks_endpoint_without_runs():
    client = TestClient(app)
    response = client.get("/api/v1/picks")
    assert response.status_code == 200
    assert "picks" in response.json()


def test_html_league_without_data():
    client = TestClient(app)
    response = client.get("/league")
    assert response.status_code == 200
    assert b"Model league" in response.content
    assert b"Season pts" in response.content


def test_league_api_without_data():
    client = TestClient(app)
    response = client.get("/api/v1/league")
    assert response.status_code == 200
    body = response.json()
    assert body["season"] == "2026-27"
    assert [row["model"] for row in body["standings"]] == ["A", "B", "C", "D"]
