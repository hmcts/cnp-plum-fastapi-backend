from sqlmodel import SQLModel, Field


class Recipe(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: str
    name: str
    ingredients: str
    method: str


class RecipeResponse(SQLModel):
    id: str
    name: str
    ingredients: str
    method: str


class RecipeListResponse(SQLModel):
    recipes: list[RecipeResponse]
