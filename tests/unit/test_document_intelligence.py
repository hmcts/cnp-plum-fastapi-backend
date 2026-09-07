from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def gateway_env(monkeypatch):
    monkeypatch.setenv(
        "AI_GATEWAY_DOCUMENT_INTELLIGENCE_URL",
        "https://gateway.example/ai/platform/v1/document-intelligence",
    )
    monkeypatch.setenv("AI_GATEWAY_SCOPE", "api://gateway/.default")
    monkeypatch.setenv("AI_GATEWAY_DOCUMENT_INTELLIGENCE_SUBSCRIPTION_KEY", "test-doc-key")


@pytest.fixture
def client():
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


def make_mock_http_response(status_code: int, content: bytes, headers: dict[str, str]):
    response = MagicMock()
    response.status_code = status_code
    response.content = content
    response.headers = httpx.Headers(headers)
    return response


def test_document_intelligence_forwards_document_and_operation_location(client):
    document = b"%PDF-1.7 test document"
    operation_location = (
        "https://gateway.example/ai/platform/v1/document-intelligence/"
        "documentModels/prebuilt-layout/analyzeResults/result-123"
    )
    mock_client = AsyncMock()
    mock_client.post.return_value = make_mock_http_response(
        202,
        b'{"status":"running"}',
        {
            "content-type": "application/json",
            "Operation-Location": operation_location,
        },
    )

    with patch("app.http_client._client", mock_client), \
         patch("app.azure_auth.get_token", AsyncMock(return_value="fake-token")):
        response = client.post(
            "/document-intelligence/prebuilt-layout?pages=1-2",
            content=document,
            headers={"content-type": "application/pdf"},
        )

    assert response.status_code == 202
    assert response.content == b'{"status":"running"}'
    assert response.headers["operation-location"] == operation_location

    args, kwargs = mock_client.post.call_args
    url = args[0]
    assert url == (
        "https://gateway.example/ai/platform/v1/document-intelligence/"
        "documentModels/prebuilt-layout:analyze"
    )
    assert kwargs["content"] == document
    assert kwargs["params"] == [("pages", "1-2")]
    assert kwargs["headers"] == {
        "Authorization": "Bearer fake-token",
        "Ocp-Apim-Subscription-Key": "test-doc-key",
        "Content-Type": "application/pdf",
    }


def test_document_intelligence_returns_502_when_gateway_unreachable(client):
    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.ConnectError("Connection refused")

    with patch("app.http_client._client", mock_client), \
         patch("app.azure_auth.get_token", AsyncMock(return_value="fake-token")):
        response = client.post(
            "/document-intelligence/prebuilt-layout",
            content=b"document",
            headers={"content-type": "application/pdf"},
        )

    assert response.status_code == 502


def test_get_document_intelligence_result_proxies_response(client):
    result = b'{"status":"succeeded","analyzeResult":{"content":"text"}}'
    mock_client = AsyncMock()
    mock_client.get.return_value = make_mock_http_response(
        200,
        result,
        {
            "content-type": "application/json",
            "x-correlation-id": "correlation-123",
        },
    )

    with patch("app.http_client._client", mock_client), \
         patch("app.azure_auth.get_token", AsyncMock(return_value="fake-token")):
        response = client.get(
            "/document-intelligence/prebuilt-layout/analyzeResults/result-123"
        )

    assert response.status_code == 200
    assert response.content == result
    assert response.headers["x-correlation-id"] == "correlation-123"

    args, kwargs = mock_client.get.call_args
    assert args[0] == (
        "https://gateway.example/ai/platform/v1/document-intelligence/"
        "documentModels/prebuilt-layout/analyzeResults/result-123"
    )
    assert kwargs["headers"] == {
        "Authorization": "Bearer fake-token",
        "Ocp-Apim-Subscription-Key": "test-doc-key",
    }


def test_get_document_intelligence_result_returns_502_when_gateway_unreachable(client):
    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.ConnectError("Connection refused")

    with patch("app.http_client._client", mock_client), \
         patch("app.azure_auth.get_token", AsyncMock(return_value="fake-token")):
        response = client.get(
            "/document-intelligence/prebuilt-layout/analyzeResults/result-123"
        )

    assert response.status_code == 502


def test_document_intelligence_requires_url(client, monkeypatch):
    monkeypatch.delenv("AI_GATEWAY_DOCUMENT_INTELLIGENCE_URL")

    with patch("app.azure_auth.get_token", AsyncMock(return_value="fake-token")):
        response = client.post(
            "/document-intelligence/prebuilt-layout",
            content=b"document",
            headers={"content-type": "application/pdf"},
        )

    assert response.status_code == 500