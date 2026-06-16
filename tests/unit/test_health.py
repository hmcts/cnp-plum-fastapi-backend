from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


def make_mock_http_client(status_code: int, json_data):
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = json_data
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    return mock_client


def test_readiness_returns_up_when_service_healthy(client):
    mock_client = make_mock_http_client(200, {"status": "UP"})
    with patch("app.http_client._client", mock_client):
        response = client.get("/health/readiness")
    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


def test_readiness_returns_500_when_service_unhealthy(client):
    mock_client = make_mock_http_client(503, {"status": "DOWN"})
    with patch("app.http_client._client", mock_client):
        response = client.get("/health/readiness")
    assert response.status_code == 500
    assert response.json() == {"status": "DOWN"}


def test_readiness_returns_500_when_service_unreachable(client):
    import httpx
    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.ConnectError("Connection refused")
    with patch("app.http_client._client", mock_client):
        response = client.get("/health/readiness")
    assert response.status_code == 500
    assert response.json() == {"status": "DOWN"}


def test_liveness_returns_up(client):
    response = client.get("/health/liveness")
    assert response.status_code == 200
    assert response.json() == {"status": "UP"}

