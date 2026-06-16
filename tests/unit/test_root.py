import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


def test_root_returns_welcome_message(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "fastapi-backend" in response.text
