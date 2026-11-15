"""Tests for the health and root endpoints.

Run with:
    pytest
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── GET /health ──────────────────────────────────────────────────────────


def test_health_returns_200():
    """The health endpoint should respond with HTTP 200."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_status_is_ok():
    """The status field should be 'ok' when the service is healthy."""
    data = client.get("/health").json()
    assert data["status"] == "ok"


def test_health_returns_app_name():
    """The app field should identify the service as ReviveOps."""
    data = client.get("/health").json()
    assert data["app"] == "ReviveOps"


def test_health_returns_version():
    """The version field should be present and non-empty."""
    data = client.get("/health").json()
    assert data["version"]   # truthy string


def test_health_response_matches_schema():
    """The response should contain exactly status, app, and version."""
    data = client.get("/health").json()
    assert set(data.keys()) == {"status", "app", "version"}


# ── GET / ────────────────────────────────────────────────────────────────


def test_root_returns_200():
    """The root endpoint should respond with HTTP 200."""
    response = client.get("/")
    assert response.status_code == 200


def test_root_returns_name_and_docs():
    """The root endpoint should include the app name and a docs pointer."""
    data = client.get("/").json()
    assert data["name"] == "ReviveOps"
    assert data["docs"] == "/docs"
