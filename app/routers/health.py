import os
import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.http_client import get_client

router = APIRouter(prefix="/health", tags=["health"])


def _recipes_health_url() -> str:
    base = os.environ.get("RECIPES_SERVICE_URL", "http://localhost:4550")
    return f"{base.rstrip('/')}/health/readiness"


@router.get("")
async def health() -> dict:
    return {"status": "UP"}


@router.get("/readiness")
async def readiness():
    try:
        response = await get_client().get(_recipes_health_url(), timeout=5.0)
        if response.status_code == 200:
            return {"status": "UP"}
        return JSONResponse(status_code=500, content={"status": "DOWN"})
    except httpx.RequestError:
        return JSONResponse(status_code=500, content={"status": "DOWN"})


@router.get("/liveness")
async def liveness() -> dict:
    return {"status": "UP"}
