import os
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from app.http_client import get_client

router = APIRouter(prefix="/recipes", tags=["recipes"])


def _recipes_base_url() -> str:
    base = os.environ.get("RECIPES_SERVICE_URL", "http://localhost:4550")
    return f"{base.rstrip('/')}/recipes"


@router.get("")
async def get_all_recipes():
    try:
        response = await get_client().get(_recipes_base_url())
        return JSONResponse(content=response.json(), status_code=response.status_code)
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Could not reach recipes service")


@router.get("/{recipe_id}")
async def get_recipe(recipe_id: str):
    try:
        response = await get_client().get(f"{_recipes_base_url()}/{recipe_id}")
        return JSONResponse(content=response.json(), status_code=response.status_code)
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Could not reach recipes service")

