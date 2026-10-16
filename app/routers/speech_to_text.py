import json
import logging
import os
from collections.abc import AsyncIterator
from uuid import uuid4

import httpx
from azure.core.exceptions import AzureError, ResourceNotFoundError
from azure.storage.blob import ContentSettings
from fastapi import APIRouter, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, Field, JsonValue

from app import azure_auth, blob_storage
from app.gateway import gateway_scope, subscription_key
from app.http_client import get_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/speech-to-text", tags=["speech-to-text"])


def _gateway_url() -> str:
    url = os.environ.get("AI_GATEWAY_SPEECH_TO_TEXT_URL")
    if not url:
        raise HTTPException(
            status_code=500,
            detail="AI_GATEWAY_SPEECH_TO_TEXT_URL is not configured",
        )
    return url.rstrip("/")


def _subscription_key() -> str:
    return subscription_key(
        "AI_GATEWAY_SPEECH_TO_TEXT_SUBSCRIPTION_KEY_FILE",
        "AI_GATEWAY_SPEECH_TO_TEXT_SUBSCRIPTION_KEY",
        "AI Gateway speech-to-text subscription key is not configured",
    )


@router.post(
    "/fast",
    summary="Transcribe an audio recording",
    description=(
        "Streams a multipart/form-data recording to the AI Gateway and returns "
        "the synchronous transcription response."
    ),
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["audio"],
                        "properties": {
                            "audio": {
                                "type": "string",
                                "format": "binary",
                                "description": "The recording to transcribe.",
                            },
                            "definition": {
                                "type": "string",
                                "description": (
                                    "Transcription options as a JSON string."
                                ),
                                "example": '{"locales":["en-GB"]}',
                            },
                        },
                    },
                    "encoding": {
                        "audio": {"contentType": "application/octet-stream"}
                    },
                }
            },
        }
    },
)
async def transcribe_audio(request: Request):
    return await _transcribe(
        request.stream(),
        request.headers.get("content-type", "multipart/form-data"),
        request.headers.get("content-length"),
        params=list(request.query_params.multi_items()),
    )


async def _transcribe(
    content: AsyncIterator[bytes],
    content_type: str,
    content_length: str | None = None,
    params: list[tuple[str, str]] | None = None,
) -> Response:
    try:
        token = await azure_auth.get_token(gateway_scope())
    except Exception:
        logger.exception("Failed to acquire AI Gateway speech-to-text token")
        raise HTTPException(status_code=500, detail="Could not acquire gateway token")

    headers = {
        "Authorization": f"Bearer {token}",
        "Ocp-Apim-Subscription-Key": _subscription_key(),
        "Content-Type": content_type,
    }
    if content_length is not None:
        headers["Content-Length"] = content_length

    try:
        response = await get_client().post(
            f"{_gateway_url()}/transcriptions:transcribe",
            content=content,
            headers=headers,
            params=params,
            timeout=300.0,
        )
    except httpx.RequestError as exc:
        logger.error("Failed to reach AI Gateway speech-to-text: %s", exc)
        raise HTTPException(status_code=502, detail="Could not reach AI Gateway")

    response_headers = {}
    for header_name in ("Content-Type", "Retry-After", "X-Correlation-Id"):
        header_value = response.headers.get(header_name)
        if header_value:
            response_headers[header_name] = header_value

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=response_headers,
    )


class AudioBlob(BaseModel):
    blob_name: str = Field(min_length=1)


class BlobTranscription(AudioBlob):
    definition: dict[str, JsonValue] | None = None


async def _audio_chunks(audio: UploadFile) -> AsyncIterator[bytes]:
    while chunk := await audio.read(1024 * 1024):
        yield chunk


@router.post(
    "/blobs",
    status_code=201,
    response_model=AudioBlob,
    summary="Upload an audio recording to blob storage",
)
async def upload_audio(audio: UploadFile) -> AudioBlob:
    blob_name = uuid4().hex
    try:
        if audio.size == 0:
            raise HTTPException(status_code=400, detail="Audio file is empty")
        blob = blob_storage.get_blob_client(blob_name)
        await blob.upload_blob(
            _audio_chunks(audio),
            length=audio.size,
            overwrite=False,
            content_settings=ContentSettings(
                content_type=audio.content_type or "application/octet-stream"
            ),
        )
    except AzureError:
        logger.exception("Failed to upload audio to blob storage")
        raise HTTPException(status_code=502, detail="Could not upload audio to blob storage")
    finally:
        await audio.close()
    return AudioBlob(blob_name=blob_name)


async def _blob_multipart(
    chunks: AsyncIterator[bytes], boundary: str, definition: dict[str, JsonValue] | None
) -> AsyncIterator[bytes]:
    yield (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="audio"; filename="audio"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode()
    async for chunk in chunks:
        yield chunk
    if definition is not None:
        yield (
            f"\r\n--{boundary}\r\n"
            'Content-Disposition: form-data; name="definition"\r\n\r\n'
        ).encode()
        yield json.dumps(definition).encode()
    yield f"\r\n--{boundary}--\r\n".encode()


@router.post(
    "/fast/blob",
    summary="Transcribe an audio recording from blob storage",
    description=(
        "Retrieves a recording from the configured container and streams it to "
        "the AI Gateway. The stored recording is retained for reuse."
    ),
)
async def transcribe_blob(body: BlobTranscription, request: Request) -> Response:
    try:
        blob = blob_storage.get_blob_client(body.blob_name)
        download = await blob.download_blob()
        boundary = uuid4().hex
        return await _transcribe(
            _blob_multipart(download.chunks(), boundary, body.definition),
            f"multipart/form-data; boundary={boundary}",
            params=list(request.query_params.multi_items()),
        )
    except ResourceNotFoundError:
        logger.info("Audio blob not found")
        raise HTTPException(status_code=404, detail="Audio blob not found")
    except AzureError:
        logger.exception("Failed to retrieve audio from blob storage")
        raise HTTPException(status_code=502, detail="Could not retrieve audio from blob storage")
