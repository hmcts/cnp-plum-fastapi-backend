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


# --- /chat/frontend endpoint tests ---

@pytest.fixture
def frontend_env(monkeypatch):
    monkeypatch.setenv("AI_GATEWAY_SUBSCRIPTION_KEY_FRONTEND", "test-frontend-sub-key")


def test_chat_frontend_returns_200_and_proxies_response(client, frontend_env):
    data = {"choices": [{"message": {"role": "assistant", "content": "hi"}}]}
    mock_client = make_mock_http_client(200, data)
    with patch("app.http_client._client", mock_client), \
         patch("app.azure_auth.get_token", AsyncMock(return_value="fake-token")):
        response = client.post("/chat/frontend", json={"messages": [{"role": "user", "content": "hi"}]})
    assert response.status_code == 200
    assert response.json() == data


def test_chat_frontend_uses_frontend_subscription_key(client, frontend_env):
    mock_client = make_mock_http_client(200, {})
    with patch("app.http_client._client", mock_client), \
         patch("app.azure_auth.get_token", AsyncMock(return_value="fake-token")):
        client.post("/chat/frontend", json={"messages": [{"role": "user", "content": "hi"}]})
    _, kwargs = mock_client.post.call_args
    assert kwargs["headers"]["Ocp-Apim-Subscription-Key"] == "test-frontend-sub-key"


def test_chat_frontend_returns_500_when_key_missing(client):
    with patch("app.azure_auth.get_token", AsyncMock(return_value="fake-token")):
        response = client.post("/chat/frontend", json={"messages": [{"role": "user", "content": "hi"}]})
    assert response.status_code == 500


def test_chat_returns_500_when_url_missing(monkeypatch, client):
    monkeypatch.delenv("AI_GATEWAY_URL")
    with patch("app.azure_auth.get_token", AsyncMock(return_value="fake-token")), \
         patch("app.http_client._client", make_mock_http_client(200, {})):
        response = client.post("/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    assert response.status_code == 500


def test_chat_returns_500_when_scope_missing(monkeypatch, client):
    monkeypatch.delenv("AI_GATEWAY_SCOPE")
    with patch("app.azure_auth.get_token", AsyncMock(return_value="fake-token")), \
         patch("app.http_client._client", make_mock_http_client(200, {})):
        response = client.post("/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    assert response.status_code == 500


def test_chat_returns_500_when_token_fails(client):
    with patch("app.azure_auth.get_token", AsyncMock(side_effect=Exception("auth error"))):
        response = client.post("/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    assert response.status_code == 500


def test_chat_frontend_returns_500_when_token_fails(client, frontend_env):
    with patch("app.azure_auth.get_token", AsyncMock(side_effect=Exception("auth error"))):
        response = client.post("/chat/frontend", json={"messages": [{"role": "user", "content": "hi"}]})
    assert response.status_code == 500


def test_chat_frontend_returns_502_when_gateway_unreachable(client, frontend_env):
    import httpx
    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.ConnectError("Connection refused")
    with patch("app.http_client._client", mock_client), \
         patch("app.azure_auth.get_token", AsyncMock(return_value="fake-token")):
        response = client.post("/chat/frontend", json={"messages": [{"role": "user", "content": "hi"}]})
    assert response.status_code == 502


def test_subscription_key_read_from_file(tmp_path, client):
    key_file = tmp_path / "sub_key"
    key_file.write_text("file-based-key\n")
    mock_client = make_mock_http_client(200, {})
    with patch("app.http_client._client", mock_client), \
         patch("app.azure_auth.get_token", AsyncMock(return_value="fake-token")), \
         patch.dict("os.environ", {"AI_GATEWAY_SUBSCRIPTION_KEY_FILE": str(key_file)}):
        client.post("/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    _, kwargs = mock_client.post.call_args
    assert kwargs["headers"]["Ocp-Apim-Subscription-Key"] == "file-based-key"


def test_frontend_subscription_key_read_from_file(tmp_path, client):
    key_file = tmp_path / "frontend_key"
    key_file.write_text("file-based-frontend-key\n")
    mock_client = make_mock_http_client(200, {})
    with patch("app.http_client._client", mock_client), \
         patch("app.azure_auth.get_token", AsyncMock(return_value="fake-token")), \
         patch.dict("os.environ", {"AI_GATEWAY_SUBSCRIPTION_KEY_FRONTEND_FILE": str(key_file)}):
        client.post("/chat/frontend", json={"messages": [{"role": "user", "content": "hi"}]})
    _, kwargs = mock_client.post.call_args
    assert kwargs["headers"]["Ocp-Apim-Subscription-Key"] == "file-based-frontend-key"
