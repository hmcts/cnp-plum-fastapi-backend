import logging
import os
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from app.http_client import get_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recipes", tags=["recipes"])


def _recipes_base_url() -> str:
    base = os.environ.get("RECIPES_SERVICE_URL", "http://localhost:4550")
    return f"{base.rstrip('/')}/recipes"


@router.get("")
async def get_all_recipes():
    logger.info("Fetching all recipes")
    try:
        response = await get_client().get(_recipes_base_url())
        logger.info("Recipes response status: %s", response.status_code)
        return JSONResponse(content=response.json(), status_code=response.status_code)
    except httpx.RequestError as exc:
        logger.error("Failed to reach recipes service: %s", exc)
        raise HTTPException(status_code=502, detail="Could not reach recipes service")


@router.get("/{recipe_id}")
async def get_recipe(recipe_id: str):
    logger.info("Fetching recipe id=%s", recipe_id)
    try:
        response = await get_client().get(f"{_recipes_base_url()}/{recipe_id}")
        logger.info("Recipe %s response status: %s", recipe_id, response.status_code)
        return JSONResponse(content=response.json(), status_code=response.status_code)
    except httpx.RequestError as exc:
        logger.error("Failed to reach recipes service for id=%s: %s", recipe_id, exc)
        raise HTTPException(status_code=502, detail="Could not reach recipes service")

