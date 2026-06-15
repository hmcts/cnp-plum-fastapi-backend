import os
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class InfoResponse(BaseModel):
    version: str
    buildNumber: str
    gitCommit: str
    date: str


@router.get("/info", response_model=InfoResponse)
async def info() -> InfoResponse:
    return InfoResponse(
        version=os.environ.get("APP_VERSION", "0.1.0"),
        buildNumber=os.environ.get("BUILD_NUMBER", "unknown"),
        gitCommit=os.environ.get("GIT_COMMIT", "unknown"),
        date=os.environ.get("BUILD_DATE", "unknown"),
    )
