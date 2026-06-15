from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import literal
from sqlmodel import select
from app.routers import root, info, recipes
from app import database
from app.database import get_db

# Uncomment to enable Azure Application Insights telemetry.
# Requires APPLICATIONINSIGHTS_CONNECTION_STRING environment variable.
# from azure.monitor.opentelemetry import configure_azure_monitor
# configure_azure_monitor()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.open_engine()
    yield
    await database.close_engine()


app = FastAPI(title="fastapi-backend", lifespan=lifespan)

app.include_router(root.router)
app.include_router(info.router)
app.include_router(recipes.router)


@app.get("/health/readiness")
async def readiness(session: AsyncSession = Depends(get_db)) -> dict:
    await session.exec(select(literal(1)))
    return {"status": "UP"}


@app.get("/health/liveness")
async def liveness() -> dict:
    return {"status": "UP"}
