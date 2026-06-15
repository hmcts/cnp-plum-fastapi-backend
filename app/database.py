import os
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

_engine = None
_session_factory: async_sessionmaker | None = None


def _build_url() -> str:
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    dbname = os.environ.get("POSTGRES_DATABASE", "plum")
    user = os.environ.get("POSTGRES_USER", "")
    password = os.environ.get("POSTGRES_PASSWORD", "")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{dbname}"


def _build_connect_args() -> dict:
    sslmode = os.environ.get("POSTGRES_SSL_MODE", "require")
    if sslmode == "disable":
        return {"ssl": False}
    return {"ssl": "require"}


async def open_engine() -> None:
    global _engine, _session_factory
    _engine = create_async_engine(
        _build_url(),
        connect_args=_build_connect_args(),
    )
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def close_engine() -> None:
    if _engine:
        await _engine.dispose()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    assert _session_factory is not None, "Database engine not initialised"
    async with _session_factory() as session:
        yield session
