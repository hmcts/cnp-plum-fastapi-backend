import platform
import tomllib
from pathlib import Path
from importlib.metadata import version
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


def _app_version() -> str:
    pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
    with open(pyproject, "rb") as f:
        return tomllib.load(f)["project"]["version"]


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
        app=_app_version(),
        dependencies=DependencyVersions(
            fastapi=version("fastapi"),
            httpx=version("httpx"),
            python=platform.python_version(),
        ),
    )
