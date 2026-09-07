import logging
import os
from urllib.parse import quote

import httpx
from fastapi import APIRouter, HTTPException, Request, Response

from app import azure_auth
from app.gateway import gateway_scope, subscription_key
from app.http_client import get_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/document-intelligence", tags=["document-intelligence"])


def _gateway_url() -> str:
    url = os.environ.get("AI_GATEWAY_DOCUMENT_INTELLIGENCE_URL")
    if not url:
        raise HTTPException(
            status_code=500,
            detail="AI_GATEWAY_DOCUMENT_INTELLIGENCE_URL is not configured",
        )
    return url.rstrip("/")


def _subscription_key() -> str:
    return subscription_key(
        "AI_GATEWAY_DOCUMENT_INTELLIGENCE_SUBSCRIPTION_KEY_FILE",
        "AI_GATEWAY_DOCUMENT_INTELLIGENCE_SUBSCRIPTION_KEY",
        "AI Gateway document intelligence subscription key is not configured",
    )


@router.post("/{model_id}")
async def analyze_document(model_id: str, request: Request):
    try:
        token = await azure_auth.get_token(gateway_scope())
    except Exception:
        logger.exception("Failed to acquire AI Gateway token")
        raise HTTPException(status_code=500, detail="Could not acquire gateway token")

    headers = {
        "Authorization": f"Bearer {token}",
        "Ocp-Apim-Subscription-Key": _subscription_key(),
        "Content-Type": request.headers.get("content-type", "application/octet-stream"),
    }
    gateway_url = f"{_gateway_url()}/documentModels/{quote(model_id, safe='')}:analyze"

    try:
        response = await get_client().post(
            gateway_url,
            content=await request.body(),
            headers=headers,
            params=list(request.query_params.multi_items()),
            timeout=30.0,
        )
    except httpx.RequestError as exc:
        logger.error("Failed to reach AI Gateway document intelligence: %s", exc)
        raise HTTPException(status_code=502, detail="Could not reach AI Gateway")

    response_headers = {}
    for header_name in ("Operation-Location", "Retry-After", "X-Correlation-Id"):
        header_value = response.headers.get(header_name)
        if header_value:
            response_headers[header_name] = header_value

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=response_headers,
        media_type=response.headers.get("content-type"),
    )


@router.get("/{model_id}/analyzeResults/{result_id}")
async def get_analyze_result(model_id: str, result_id: str):
    try:
        token = await azure_auth.get_token(gateway_scope())
    except Exception:
        logger.exception("Failed to acquire AI Gateway token")
        raise HTTPException(status_code=500, detail="Could not acquire gateway token")

    headers = {
        "Authorization": f"Bearer {token}",
        "Ocp-Apim-Subscription-Key": _subscription_key(),
    }
    gateway_url = (
        f"{_gateway_url()}/documentModels/{quote(model_id, safe='')}"
        f"/analyzeResults/{quote(result_id, safe='')}"
    )

    try:
        response = await get_client().get(gateway_url, headers=headers, timeout=30.0)
    except httpx.RequestError as exc:
        logger.error("Failed to reach AI Gateway document intelligence: %s", exc)
        raise HTTPException(status_code=502, detail="Could not reach AI Gateway")

    response_headers = {}
    for header_name in ("Retry-After", "X-Correlation-Id"):
        header_value = response.headers.get(header_name)
        if header_value:
            response_headers[header_name] = header_value

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=response_headers,
        media_type=response.headers.get("content-type"),
    )