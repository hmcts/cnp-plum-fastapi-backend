from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def gateway_env(monkeypatch):
    monkeypatch.setenv(
        "AI_GATEWAY_SPEECH_TO_TEXT_URL",
        "https://gateway.example/ai/platform/v1/speech-to-text/fast/",
    )
    monkeypatch.setenv("AI_GATEWAY_SCOPE", "api://gateway/.default")
    monkeypatch.setenv(
        "AI_GATEWAY_SPEECH_TO_TEXT_SUBSCRIPTION_KEY",
        "test-speech-key",
    )


@pytest.fixture
def client():
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


def make_mock_http_response(
    status_code: int, content: bytes, headers: dict[str, str]
):
    response = MagicMock()
    response.status_code = status_code
    response.content = content
    response.headers = httpx.Headers(headers)
    return response


async def read_stream(content) -> bytes:
    chunks = []
    async for chunk in content:
        chunks.append(chunk)
    return b"".join(chunks)


def multipart_body() -> tuple[bytes, str]:
    boundary = "speech-test-boundary"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="audio"; filename="test.wav"\r\n'
        "Content-Type: audio/wav\r\n"
        "\r\n"
        "audio bytes\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="definition"\r\n'
        "\r\n"
        '{"locales":["en-GB"]}\r\n'
        f"--{boundary}--\r\n"
    ).encode()
    return body, f"multipart/form-data; boundary={boundary}"


@pytest.mark.asyncio
async def test_speech_to_text_streams_multipart_request_and_proxies_response(client):
    body, content_type = multipart_body()
    response_body = b'{"combinedPhrases":[{"text":"hello"}],"phrases":[]}'
    mock_client = AsyncMock()
    mock_client.post.return_value = make_mock_http_response(
        200,
        response_body,
        {"content-type": "application/json"},
    )

    with patch("app.http_client._client", mock_client), patch(
        "app.azure_auth.get_token", AsyncMock(return_value="fake-token")
    ):
        response = client.post(
            "/speech-to-text/fast",
            content=body,
            headers={
                "content-type": content_type,
                "content-length": str(len(body)),
            },
        )

    assert response.status_code == 200
    assert response.content == response_body

    args, kwargs = mock_client.post.call_args
    assert args[0] == (
        "https://gateway.example/ai/platform/v1/speech-to-text/fast/"
        "transcriptions:transcribe"
    )
    assert await read_stream(kwargs["content"]) == body
    assert kwargs["headers"] == {
        "Authorization": "Bearer fake-token",
        "Ocp-Apim-Subscription-Key": "test-speech-key",
        "Content-Type": content_type,
        "Content-Length": str(len(body)),
    }
    assert kwargs["timeout"] == 300.0


def test_speech_to_text_proxies_gateway_error_and_operational_headers(client):
    body, content_type = multipart_body()
    response_body = b'{"error":{"code":"payload_too_large"}}'
    mock_client = AsyncMock()
    mock_client.post.return_value = make_mock_http_response(
        413,
        response_body,
        {
            "content-type": "application/json",
            "retry-after": "30",
            "x-correlation-id": "correlation-123",
        },
    )

    with patch("app.http_client._client", mock_client), patch(
        "app.azure_auth.get_token", AsyncMock(return_value="fake-token")
    ):
        response = client.post(
            "/speech-to-text/fast",
            content=body,
            headers={"content-type": content_type},
        )

    assert response.status_code == 413
    assert response.content == response_body
    assert response.headers["content-type"] == "application/json"
    assert response.headers["retry-after"] == "30"
    assert response.headers["x-correlation-id"] == "correlation-123"


@pytest.mark.parametrize(
    "error",
    [httpx.ConnectError("Connection refused"), httpx.ReadTimeout("Timed out")],
)
def test_speech_to_text_returns_502_when_gateway_unreachable(client, error):
    mock_client = AsyncMock()
    mock_client.post.side_effect = error

    with patch("app.http_client._client", mock_client), patch(
        "app.azure_auth.get_token", AsyncMock(return_value="fake-token")
    ):
        response = client.post("/speech-to-text/fast", content=b"audio")

    assert response.status_code == 502


def test_speech_to_text_requires_url(client, monkeypatch):
    monkeypatch.delenv("AI_GATEWAY_SPEECH_TO_TEXT_URL")

    with patch("app.azure_auth.get_token", AsyncMock(return_value="fake-token")):
        response = client.post("/speech-to-text/fast", content=b"audio")

    assert response.status_code == 500


def test_speech_to_text_requires_subscription_key(client, monkeypatch):
    monkeypatch.delenv("AI_GATEWAY_SPEECH_TO_TEXT_SUBSCRIPTION_KEY")

    with patch("app.azure_auth.get_token", AsyncMock(return_value="fake-token")):
        response = client.post("/speech-to-text/fast", content=b"audio")

    assert response.status_code == 500


def test_speech_to_text_requires_scope(client, monkeypatch):
    monkeypatch.delenv("AI_GATEWAY_SCOPE")

    with patch("app.azure_auth.get_token", AsyncMock(return_value="fake-token")):
        response = client.post("/speech-to-text/fast", content=b"audio")

    assert response.status_code == 500


def test_speech_to_text_returns_500_when_token_acquisition_fails(client):
    with patch(
        "app.azure_auth.get_token",
        AsyncMock(side_effect=Exception("auth error")),
    ):
        response = client.post("/speech-to-text/fast", content=b"audio")

    assert response.status_code == 500


def test_speech_to_text_reads_subscription_key_from_file(tmp_path, client):
    key_file = tmp_path / "speech-subscription-key"
    key_file.write_text("file-based-key\n")
    mock_client = AsyncMock()
    mock_client.post.return_value = make_mock_http_response(200, b"{}", {})

    with patch("app.http_client._client", mock_client), patch(
        "app.azure_auth.get_token", AsyncMock(return_value="fake-token")
    ), patch.dict(
        "os.environ",
        {"AI_GATEWAY_SPEECH_TO_TEXT_SUBSCRIPTION_KEY_FILE": str(key_file)},
    ):
        client.post("/speech-to-text/fast", content=b"audio")

    _, kwargs = mock_client.post.call_args
    assert kwargs["headers"]["Ocp-Apim-Subscription-Key"] == "file-based-key"


def test_speech_to_text_openapi_documents_multipart_fields(client):
    from app.main import app

    operation = app.openapi()["paths"]["/speech-to-text/fast"]["post"]
    request_body = operation["requestBody"]["content"]["multipart/form-data"]
    schema = request_body["schema"]

    assert schema["required"] == ["audio"]
    assert schema["properties"]["audio"] == {
        "type": "string",
        "format": "binary",
        "description": "The recording to transcribe.",
    }
    assert schema["properties"]["definition"]["type"] == "string"
