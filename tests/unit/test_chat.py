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
    mock_client.post.return_value = make_mock_http_response(status_code, json_data)
    return mock_client


@pytest.fixture(autouse=True)
def gateway_env(monkeypatch):
    monkeypatch.setenv("AI_GATEWAY_URL", "https://gateway.example/chat/completions")
    monkeypatch.setenv("AI_GATEWAY_SCOPE", "api://gateway/.default")
    monkeypatch.setenv("AI_GATEWAY_SUBSCRIPTION_KEY", "test-sub-key")
    monkeypatch.setenv("AI_GATEWAY_MODEL", "gpt-5.5")


@pytest.fixture
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


def test_chat_returns_200_and_proxies_response(client):
    data = {"choices": [{"message": {"role": "assistant", "content": "hi"}}]}
    mock_client = make_mock_http_client(200, data)
    with patch("app.http_client._client", mock_client), \
         patch("app.azure_auth.get_token", AsyncMock(return_value="fake-token")):
        response = client.post("/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    assert response.status_code == 200
    assert response.json() == data


def test_chat_forwards_bearer_and_subscription_headers(client):
    mock_client = make_mock_http_client(200, {})
    with patch("app.http_client._client", mock_client), \
         patch("app.azure_auth.get_token", AsyncMock(return_value="fake-token")):
        client.post("/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    _, kwargs = mock_client.post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer fake-token"
    assert kwargs["headers"]["Ocp-Apim-Subscription-Key"] == "test-sub-key"


def test_chat_injects_default_model_when_absent(client):
    mock_client = make_mock_http_client(200, {})
    with patch("app.http_client._client", mock_client), \
         patch("app.azure_auth.get_token", AsyncMock(return_value="fake-token")):
        client.post("/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    _, kwargs = mock_client.post.call_args
    assert kwargs["json"]["model"] == "gpt-5.5"


def test_chat_proxies_gateway_error_status(client):
    mock_client = make_mock_http_client(400, {"error": {"code": "content_filter"}})
    with patch("app.http_client._client", mock_client), \
         patch("app.azure_auth.get_token", AsyncMock(return_value="fake-token")):
        response = client.post("/chat", json={"messages": [{"role": "user", "content": "x"}]})
    assert response.status_code == 400


def test_chat_returns_502_when_gateway_unreachable(client):
    import httpx
    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.ConnectError("Connection refused")
    with patch("app.http_client._client", mock_client), \
         patch("app.azure_auth.get_token", AsyncMock(return_value="fake-token")):
        response = client.post("/chat", json={"messages": [{"role": "user", "content": "x"}]})
    assert response.status_code == 502


def test_chat_requires_messages(client):
    with patch("app.azure_auth.get_token", AsyncMock(return_value="fake-token")):
        response = client.post("/chat", json={})
    assert response.status_code == 422
