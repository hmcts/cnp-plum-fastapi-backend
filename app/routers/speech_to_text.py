import logging
import os

import httpx
from fastapi import APIRouter, HTTPException, Request, Response

from app import azure_auth
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
    try:
        token = await azure_auth.get_token(gateway_scope())
    except Exception:
        logger.exception("Failed to acquire AI Gateway speech-to-text token")
        raise HTTPException(status_code=500, detail="Could not acquire gateway token")

    headers = {
        "Authorization": f"Bearer {token}",
        "Ocp-Apim-Subscription-Key": _subscription_key(),
        "Content-Type": request.headers.get("content-type", "multipart/form-data"),
    }
    content_length = request.headers.get("content-length")
    if content_length is not None:
        headers["Content-Length"] = content_length

    try:
        response = await get_client().post(
            f"{_gateway_url()}/transcriptions:transcribe",
            content=request.stream(),
            headers=headers,
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
