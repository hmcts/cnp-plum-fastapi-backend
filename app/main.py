from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.routers import root, info, recipes, health
from app import http_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    await http_client.open_client()
    yield
    await http_client.close_client()


app = FastAPI(
    title="fastapi-backend",
    lifespan=lifespan,
)

app.include_router(root.router)
app.include_router(info.router)
app.include_router(recipes.router)
app.include_router(health.router)
