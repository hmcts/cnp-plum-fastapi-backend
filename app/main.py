import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.routers import root, info, recipes, health, chat
from app import http_client, azure_auth

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("plum-fastapi-backend starting up")
    await http_client.open_client()
    yield
    await http_client.close_client()
    await azure_auth.close_credential()
    logger.info("plum-fastapi-backend shut down")


app = FastAPI(
    title="fastapi-backend",
    lifespan=lifespan,
)

app.include_router(root.router)
app.include_router(info.router)
app.include_router(recipes.router)
app.include_router(health.router)
app.include_router(chat.router)

# Test Jenkins deployment