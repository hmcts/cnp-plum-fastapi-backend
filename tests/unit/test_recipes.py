from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient


def make_mock_http_response(status_code: int, json_data):
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = json_data
    return mock_response


def make_mock_http_client(status_code: int, json_data):
    mock_client = AsyncMock()
    mock_client.get.return_value = make_mock_http_response(status_code, json_data)
    return mock_client


@pytest.fixture
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


def test_get_all_recipes_returns_200(client):
    mock_client = make_mock_http_client(200, [{"id": "1", "name": "Pasta"}])
    with patch("app.http_client._client", mock_client):
        response = client.get("/recipes")
    assert response.status_code == 200


def test_get_all_recipes_proxies_response(client):
    data = [{"id": "recipe-1", "name": "Tomato Pasta"}]
    mock_client = make_mock_http_client(200, data)
    with patch("app.http_client._client", mock_client):
        response = client.get("/recipes")
    assert response.json() == data


def test_get_all_recipes_returns_502_when_service_unreachable(client):
    import httpx
    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.ConnectError("Connection refused")
    with patch("app.http_client._client", mock_client):
        response = client.get("/recipes")
    assert response.status_code == 502


def test_get_recipe_by_id_returns_200(client):
    data = {"id": "recipe-1", "name": "Tomato Pasta"}
    mock_client = make_mock_http_client(200, data)
    with patch("app.http_client._client", mock_client):
        response = client.get("/recipes/recipe-1")
    assert response.status_code == 200


def test_get_recipe_by_id_proxies_response(client):
    data = {"id": "recipe-1", "name": "Tomato Pasta"}
    mock_client = make_mock_http_client(200, data)
    with patch("app.http_client._client", mock_client):
        response = client.get("/recipes/recipe-1")
    assert response.json() == data


def test_get_recipe_by_id_proxies_404(client):
    mock_client = make_mock_http_client(404, {"detail": "Not found"})
    with patch("app.http_client._client", mock_client):
        response = client.get("/recipes/nonexistent")
    assert response.status_code == 404


def test_get_recipe_calls_correct_url(client, monkeypatch):
    monkeypatch.setenv("RECIPES_SERVICE_URL", "http://test-service:4550")
    mock_client = make_mock_http_client(200, [])
    with patch("app.http_client._client", mock_client):
        client.get("/recipes")
    mock_client.get.assert_called_once_with("http://test-service:4550/recipes")


def test_get_recipe_by_id_returns_502_when_service_unreachable(client):
    import httpx
    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.ConnectError("Connection refused")
    with patch("app.http_client._client", mock_client):
        response = client.get("/recipes/recipe-1")
    assert response.status_code == 502

