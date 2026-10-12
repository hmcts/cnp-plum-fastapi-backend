from unittest.mock import AsyncMock, MagicMock, patch
from email.parser import BytesParser
from email.policy import default

import httpx
import pytest
from azure.core.exceptions import AzureError, ResourceNotFoundError
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


def test_upload_audio_stores_only_audio_and_returns_unique_blob_name(client):
    blob = AsyncMock()
    uploaded = []

    async def upload(content, **kwargs):
        uploaded.append(await read_stream(content))

    blob.upload_blob.side_effect = upload
    with patch("app.blob_storage.get_blob_client", return_value=blob) as get_blob:
        first = client.post(
            "/speech-to-text/blobs", files={"audio": ("sample.wav", b"first", "audio/wav")}
        )
        second = client.post(
            "/speech-to-text/blobs", files={"audio": ("sample.wav", b"second", "audio/wav")}
        )

    assert first.status_code == second.status_code == 201
    assert first.json()["blob_name"] != second.json()["blob_name"]
    assert get_blob.call_args_list[0].args == (first.json()["blob_name"],)
    assert uploaded == [b"first", b"second"]
    kwargs = blob.upload_blob.call_args.kwargs
    assert kwargs["length"] == 6
    assert kwargs["overwrite"] is False
    assert kwargs["content_settings"].content_type == "audio/wav"


def test_upload_rejects_empty_audio(client):
    with patch("app.blob_storage.get_blob_client") as get_blob:
        response = client.post("/speech-to-text/blobs", files={"audio": ("empty.wav", b"")})
    assert response.status_code == 400
    get_blob.assert_not_called()


def test_upload_requires_audio_field(client):
    response = client.post("/speech-to-text/blobs", files={"other": ("sample.wav", b"audio")})
    assert response.status_code == 422


def test_upload_storage_failure(client):
    blob = AsyncMock()
    blob.upload_blob.side_effect = AzureError("Storage unavailable")
    with patch("app.blob_storage.get_blob_client", return_value=blob):
        response = client.post("/speech-to-text/blobs", files={"audio": ("sample.wav", b"audio")})
    assert response.status_code == 502
    assert response.json()["detail"] == "Could not upload audio to blob storage"


async def blob_chunks():
    yield b"audio "
    yield b"bytes"


@pytest.mark.parametrize("definition", [None, {}, {"locales": ["en-GB"]}])
def test_transcribe_blob_streams_download_and_options(client, definition):
    blob = AsyncMock()
    download = MagicMock()
    download.chunks.return_value = blob_chunks()
    blob.download_blob.return_value = download
    gateway = AsyncMock()
    sent = []

    async def post(*args, **kwargs):
        sent.append(await read_stream(kwargs["content"]))
        return make_mock_http_response(
            200, b'{"text":"hello"}', {"content-type": "application/json"}
        )

    gateway.post.side_effect = post
    with patch("app.blob_storage.get_blob_client", return_value=blob) as get_blob, patch(
        "app.http_client._client", gateway
    ), patch("app.azure_auth.get_token", AsyncMock(return_value="fake-token")):
        response = client.post(
            "/speech-to-text/fast/blob",
            json={"blob_name": "folder/audio.wav", "definition": definition},
        )

    assert response.status_code == 200
    assert response.json() == {"text": "hello"}
    get_blob.assert_called_once_with("folder/audio.wav")
    blob.download_blob.assert_awaited_once()
    blob.delete_blob.assert_not_called()
    kwargs = gateway.post.call_args.kwargs
    boundary = kwargs["headers"]["Content-Type"].split("boundary=")[1]
    assert b'name="audio"; filename="audio"' in sent[0]
    assert b"\r\n\r\naudio bytes\r\n" in sent[0]
    assert sent[0].endswith(f"--{boundary}--\r\n".encode())
    multipart = BytesParser(policy=default).parsebytes(
        f"Content-Type: {kwargs['headers']['Content-Type']}\r\n\r\n".encode() + sent[0]
    )
    parts = list(multipart.iter_parts())
    assert parts[0].get_param("name", header="content-disposition") == "audio"
    assert parts[0].get_payload(decode=True) == b"audio bytes"
    assert len(parts) == (1 if definition is None else 2)
    assert (b'name="definition"' in sent[0]) is (definition is not None)
    if definition and "locales" in definition:
        assert b'{"locales": ["en-GB"]}' in sent[0]
    assert "Content-Length" not in kwargs["headers"]


@pytest.mark.parametrize(
    "error, status", [(ResourceNotFoundError("Not found"), 404), (AzureError("Failure"), 502)]
)
def test_transcribe_blob_storage_failure(client, error, status):
    blob = AsyncMock()
    blob.download_blob.side_effect = error
    with patch("app.blob_storage.get_blob_client", return_value=blob), patch(
        "app.http_client._client", AsyncMock()
    ) as gateway:
        response = client.post("/speech-to-text/fast/blob", json={"blob_name": "audio"})
    assert response.status_code == status
    gateway.post.assert_not_called()


def test_transcribe_blob_failure_during_streaming_is_reported(client):
    async def failing_chunks():
        yield b"partial audio"
        raise AzureError("Download interrupted")

    blob = AsyncMock()
    download = MagicMock()
    download.chunks.return_value = failing_chunks()
    blob.download_blob.return_value = download
    gateway = AsyncMock()

    async def post(*args, **kwargs):
        await read_stream(kwargs["content"])

    gateway.post.side_effect = post
    with patch("app.blob_storage.get_blob_client", return_value=blob), patch(
        "app.http_client._client", gateway
    ), patch("app.azure_auth.get_token", AsyncMock(return_value="fake-token")):
        response = client.post("/speech-to-text/fast/blob", json={"blob_name": "audio"})
    assert response.status_code == 502
    assert response.json()["detail"] == "Could not retrieve audio from blob storage"


@pytest.mark.parametrize(
    "body", [{}, {"blob_name": ""}, {"blob_name": "audio", "definition": "not an object"}]
)
def test_transcribe_blob_validates_request(client, body):
    with patch("app.blob_storage.get_blob_client") as get_blob:
        response = client.post("/speech-to-text/fast/blob", json=body)
    assert response.status_code == 422
    get_blob.assert_not_called()


def test_transcribe_blob_proxies_gateway_errors(client):
    blob = AsyncMock()
    download = MagicMock()
    download.chunks.return_value = blob_chunks()
    blob.download_blob.return_value = download
    gateway = AsyncMock()
    gateway.post.return_value = make_mock_http_response(
        429, b'{"error":"rate limited"}',
        {"retry-after": "10", "x-correlation-id": "blob-request"},
    )
    with patch("app.blob_storage.get_blob_client", return_value=blob), patch(
        "app.http_client._client", gateway
    ), patch("app.azure_auth.get_token", AsyncMock(return_value="fake-token")):
        response = client.post("/speech-to-text/fast/blob", json={"blob_name": "audio"})
    assert response.status_code == 429
    assert response.json() == {"error": "rate limited"}
    assert response.headers["retry-after"] == "10"
    assert response.headers["x-correlation-id"] == "blob-request"


@pytest.mark.parametrize("endpoint", ["/speech-to-text/blobs", "/speech-to-text/fast/blob"])
def test_blob_endpoints_require_storage_configuration(client, monkeypatch, endpoint):
    monkeypatch.delenv("SPEECH_AUDIO_STORAGE_ACCOUNT_URL", raising=False)
    if endpoint.endswith("/blobs"):
        response = client.post(endpoint, files={"audio": ("audio.wav", b"audio")})
    else:
        response = client.post(endpoint, json={"blob_name": "audio"})
    assert response.status_code == 500
    assert response.json()["detail"] == "SPEECH_AUDIO_STORAGE_ACCOUNT_URL is not configured"


def test_blob_openapi_documents_upload_and_transcription(client):
    from app.main import app

    schema = app.openapi()
    upload = schema["paths"]["/speech-to-text/blobs"]["post"]
    assert "multipart/form-data" in upload["requestBody"]["content"]
    operation = schema["paths"]["/speech-to-text/fast/blob"]["post"]
    assert operation["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/BlobTranscription"
    )
    body = schema["components"]["schemas"]["BlobTranscription"]
    assert body["required"] == ["blob_name"]
