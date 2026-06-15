from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.routers import root, info, recipes, health
from app import database


@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.open_engine()
    yield
    await database.close_engine()


app = FastAPI(
    title="fastapi-backend",
    lifespan=lifespan,
)

app.include_router(root.router)
app.include_router(info.router)
app.include_router(recipes.router)
app.include_router(health.router)
