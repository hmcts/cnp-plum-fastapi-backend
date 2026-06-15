from fastapi import APIRouter, Depends
from sqlalchemy import literal
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/readiness")
async def readiness(session: AsyncSession = Depends(get_db)) -> dict:
    await session.exec(select(literal(1)))
    return {"status": "UP"}


@router.get("/liveness")
async def liveness() -> dict:
    return {"status": "UP"}
