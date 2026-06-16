import os
from collections.abc import AsyncGenerator
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker | None = None


def _build_url() -> URL:
    return URL.create(
        drivername="postgresql+asyncpg",
        username=os.environ.get("POSTGRES_USER", ""),
        password=os.environ.get("POSTGRES_PASSWORD", ""),
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database=os.environ.get("POSTGRES_DATABASE", "plum"),
    )


def _build_connect_args() -> dict:
    sslmode = os.environ.get("POSTGRES_SSL_MODE", "require")
    if sslmode == "disable":
        return {"ssl": False}
    return {"ssl": "require"}


async def open_engine() -> None:
    global _engine, _session_factory
    _engine = create_async_engine(
        _build_url(),
        connect_args={**_build_connect_args(), "command_timeout": 10},
        pool_pre_ping=True,
    )
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def close_engine() -> None:
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    if _session_factory is None:
        raise RuntimeError("Database engine not initialised — was open_engine() called?")
    async with _session_factory() as session:
        yield session
