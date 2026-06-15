import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock())
    return session


@pytest.fixture
def client(mock_session):
    from app.main import app
    from app.database import get_db

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_readiness_returns_up(client):
    response = client.get("/health/readiness")
    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


def test_liveness_returns_up():
    from app.main import app
    with TestClient(app) as c:
        response = c.get("/health/liveness")
    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


def test_readiness_returns_500_when_db_unavailable():
    from app.main import app
    from app.database import get_db
    from sqlalchemy.exc import OperationalError

    async def broken_db():
        raise OperationalError("Connection refused", None, None)
        yield

    app.dependency_overrides[get_db] = broken_db
    with TestClient(app, raise_server_exceptions=False) as c:
        response = c.get("/health/readiness")
    app.dependency_overrides.clear()
    assert response.status_code == 500
