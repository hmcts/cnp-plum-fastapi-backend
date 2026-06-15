import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


def test_info_returns_200(client):
    response = client.get("/info")
    assert response.status_code == 200


def test_info_contains_version(client):
    response = client.get("/info")
    assert "version" in response.json()


def test_info_contains_build_number(client):
    response = client.get("/info")
    assert "buildNumber" in response.json()


def test_info_contains_git_commit(client):
    response = client.get("/info")
    assert "gitCommit" in response.json()


def test_info_contains_date(client):
    response = client.get("/info")
    assert "date" in response.json()


def test_info_build_number_is_string(client):
    response = client.get("/info")
    assert isinstance(response.json()["buildNumber"], str)


def test_info_git_commit_is_string(client):
    response = client.get("/info")
    assert isinstance(response.json()["gitCommit"], str)


def test_info_date_is_string(client):
    response = client.get("/info")
    assert isinstance(response.json()["date"], str)


def test_info_reads_env_vars(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "1.2.3")
    monkeypatch.setenv("BUILD_NUMBER", "99")
    monkeypatch.setenv("GIT_COMMIT", "abc123")
    monkeypatch.setenv("BUILD_DATE", "2026-06-15")
    from app.main import app
    with TestClient(app) as c:
        data = c.get("/info").json()
    assert data["version"] == "1.2.3"
    assert data["buildNumber"] == "99"
    assert data["gitCommit"] == "abc123"
    assert data["date"] == "2026-06-15"


def test_info_defaults_when_env_vars_absent(monkeypatch):
    for key in ("APP_VERSION", "BUILD_NUMBER", "GIT_COMMIT", "BUILD_DATE"):
        monkeypatch.delenv(key, raising=False)
    from app.main import app
    with TestClient(app) as c:
        data = c.get("/info").json()
    assert data["version"] == "0.1.0"
    assert data["buildNumber"] == "unknown"
    assert data["gitCommit"] == "unknown"
    assert data["date"] == "unknown"
