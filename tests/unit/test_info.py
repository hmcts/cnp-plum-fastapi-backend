import platform
from importlib.metadata import version
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


def test_info_returns_200(client):
    response = client.get("/info")
    assert response.status_code == 200


def test_info_contains_app_version(client):
    data = client.get("/info").json()
    assert "app" in data
    assert isinstance(data["app"], str)


def test_info_app_version_matches_package(client):
    data = client.get("/info").json()
    assert data["app"] == version("plum-fastapi-backend")


def test_info_contains_dependencies(client):
    data = client.get("/info").json()
    assert "dependencies" in data


def test_info_fastapi_version(client):
    data = client.get("/info").json()
    assert data["dependencies"]["fastapi"] == version("fastapi")


def test_info_httpx_version(client):
    data = client.get("/info").json()
    assert data["dependencies"]["httpx"] == version("httpx")


def test_info_python_version(client):
    data = client.get("/info").json()
    assert data["dependencies"]["python"] == platform.python_version()


def test_info_no_env_vars_needed(monkeypatch):
    for key in ("APP_VERSION", "BUILD_NUMBER", "GIT_COMMIT", "BUILD_DATE"):
        monkeypatch.delenv(key, raising=False)
    from app.main import app
    with TestClient(app) as c:
        response = c.get("/info")
    assert response.status_code == 200
