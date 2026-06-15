from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from app.routers import root, info, recipes, health
from app import database



_ENABLE_DOCS = os.environ.get("ENABLE_DOCS", "false").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.open_engine()
    yield
    await database.close_engine()


app = FastAPI(
    title="fastapi-backend",
    lifespan=lifespan,
    docs_url="/docs" if _ENABLE_DOCS else None,
    redoc_url="/redoc" if _ENABLE_DOCS else None,
    openapi_url="/openapi.json" if _ENABLE_DOCS else None,
)

app.include_router(root.router)
app.include_router(info.router)
app.include_router(recipes.router)
app.include_router(health.router)
