import logging
import os
import httpx
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.http_client import get_client
from app import azure_auth
from app.gateway import gateway_scope, subscription_key

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
    return gateway_scope()


def _subscription_key() -> str:
    return subscription_key(
        "AI_GATEWAY_SUBSCRIPTION_KEY_FILE",
        "AI_GATEWAY_SUBSCRIPTION_KEY",
        "AI Gateway subscription key is not configured",
    )


def _frontend_subscription_key() -> str:
    return subscription_key(
        "AI_GATEWAY_SUBSCRIPTION_KEY_FRONTEND_FILE",
        "AI_GATEWAY_SUBSCRIPTION_KEY_FRONTEND",
        "AI Gateway frontend subscription key is not configured",
    )


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


@router.post("/frontend")
async def chat_frontend(
    request: ChatRequest,
    internal_team: str | None = Header(None, alias="x-internal-team"),
):
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
        "Ocp-Apim-Subscription-Key": _frontend_subscription_key(),
        "Content-Type": "application/json",
    }

    if internal_team is not None:
        headers["x-internal-team"] = internal_team

    try:
        response = await get_client().post(
            _gateway_url(), json=payload, headers=headers, timeout=30.0
        )
        return JSONResponse(content=response.json(), status_code=response.status_code)
    except httpx.RequestError as exc:
        logger.error("Failed to reach AI Gateway: %s", exc)
        raise HTTPException(status_code=502, detail="Could not reach AI Gateway")
