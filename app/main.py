import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.routers import root, info, recipes, health
from app import http_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("plum-fastapi-backend starting up")
    await http_client.open_client()
    yield
    await http_client.close_client()
    logger.info("plum-fastapi-backend shut down")


app = FastAPI(
    title="fastapi-backend",
    lifespan=lifespan,
)

app.include_router(root.router)
app.include_router(info.router)
app.include_router(recipes.router)
app.include_router(health.router)

# Test Jenkins deployment