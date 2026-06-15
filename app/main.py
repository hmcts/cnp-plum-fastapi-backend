from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.routers import root, info
from app import database

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


@app.get("/health/readiness")
async def readiness() -> dict:
    return {"status": "UP"}


@app.get("/health/liveness")
async def liveness() -> dict:
    return {"status": "UP"}
