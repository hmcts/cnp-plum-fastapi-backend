from fastapi import FastAPI
from app.routers import root

# Uncomment to enable Azure Application Insights telemetry.
# Requires APPLICATIONINSIGHTS_CONNECTION_STRING environment variable.
# from azure.monitor.opentelemetry import configure_azure_monitor
# configure_azure_monitor()

app = FastAPI(title="fastapi-backend")

app.include_router(root.router)


@app.get("/health/readiness")
async def readiness() -> dict:
    return {"status": "UP"}


@app.get("/health/liveness")
async def liveness() -> dict:
    return {"status": "UP"}
