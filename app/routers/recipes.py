from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.database import get_db
from app.models import Recipe, RecipeListResponse, RecipeResponse

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("", response_model=RecipeListResponse)
async def get_all_recipes(session: AsyncSession = Depends(get_db)) -> RecipeListResponse:
    result = await session.exec(select(Recipe))
    recipes = result.all()
    return RecipeListResponse(recipes=[RecipeResponse.model_validate(r, from_attributes=True) for r in recipes])


@router.get("/{recipe_id}", response_model=RecipeResponse)
async def get_recipe(recipe_id: str, session: AsyncSession = Depends(get_db)) -> RecipeResponse:
    recipe = await session.get(Recipe, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return RecipeResponse.model_validate(recipe, from_attributes=True)
