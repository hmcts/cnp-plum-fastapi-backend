import platform
from importlib.metadata import version
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class DependencyVersions(BaseModel):
    fastapi: str
    httpx: str
    python: str


class InfoResponse(BaseModel):
    app: str
    dependencies: DependencyVersions


@router.get("/info", response_model=InfoResponse)
async def info() -> InfoResponse:
    return InfoResponse(
        app=version("plum-fastapi-backend"),
        dependencies=DependencyVersions(
            fastapi=version("fastapi"),
            httpx=version("httpx"),
            python=platform.python_version(),
        ),
    )
