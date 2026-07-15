import logging
import os
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.http_client import get_client
from app import azure_auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    messages: list[dict]
    model: str | None = None


def _gateway_url() -> str:
    url = os.environ.get("AI_GATEWAY_URL")
    if not url:
        raise HTTPException(status_code=500, detail="AI_GATEWAY_URL is not configured")
    return url


def _gateway_scope() -> str:
    scope = os.environ.get("AI_GATEWAY_SCOPE")
    if not scope:
        raise HTTPException(status_code=500, detail="AI_GATEWAY_SCOPE is not configured")
    return scope


def _subscription_key() -> str:
    key_file = os.environ.get("AI_GATEWAY_SUBSCRIPTION_KEY_FILE")
    if key_file:
        with open(key_file) as f:
            return f.read().strip()
    key = os.environ.get("AI_GATEWAY_SUBSCRIPTION_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="AI Gateway subscription key is not configured")
    return key


@router.post("")
async def chat(request: ChatRequest):
    payload: dict = {"messages": request.messages}
    model = request.model or os.environ.get("AI_GATEWAY_MODEL")
    if model:
        payload["model"] = model

    try:
        token = await azure_auth.get_token(_gateway_scope())
    except Exception:
        logger.exception("Failed to acquire AI Gateway token")
        raise HTTPException(status_code=500, detail="Could not acquire gateway token")

    headers = {
        "Authorization": f"Bearer {token}",
        "Ocp-Apim-Subscription-Key": _subscription_key(),
        "Content-Type": "application/json",
    }

    try:
        response = await get_client().post(
            _gateway_url(), json=payload, headers=headers, timeout=30.0
        )
        return JSONResponse(content=response.json(), status_code=response.status_code)
    except httpx.RequestError as exc:
        logger.error("Failed to reach AI Gateway: %s", exc)
        raise HTTPException(status_code=502, detail="Could not reach AI Gateway")
