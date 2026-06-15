import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.models import Recipe


def make_recipe(id_, name, ingredients, method):
    return Recipe(
        id=id_,
        user_id="test-user",
        name=name,
        ingredients=ingredients,
        method=method,
    )


@pytest.fixture
def mock_session():
    session = AsyncMock()

    all_result = MagicMock()
    all_result.all.return_value = [
        make_recipe("recipe-1", "Tomato Pasta", "tomatoes,pasta", "Boil pasta. Make sauce."),
        make_recipe("recipe-2", "Salad", "lettuce,cucumber", "Toss ingredients."),
    ]
    session.exec = AsyncMock(return_value=all_result)
    session.get = AsyncMock(
        return_value=make_recipe("recipe-1", "Tomato Pasta", "tomatoes,pasta", "Boil pasta. Make sauce.")
    )
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


@pytest.fixture
def client_404(mock_session):
    from app.main import app
    from app.database import get_db

    mock_session.get = AsyncMock(return_value=None)

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_get_all_recipes_returns_200(client):
    response = client.get("/recipes")
    assert response.status_code == 200


def test_get_all_recipes_returns_list(client):
    response = client.get("/recipes")
    data = response.json()
    assert "recipes" in data
    assert isinstance(data["recipes"], list)
    assert len(data["recipes"]) == 2


def test_get_all_recipes_returns_correct_fields(client):
    response = client.get("/recipes")
    recipe = response.json()["recipes"][0]
    assert recipe["id"] == "recipe-1"
    assert recipe["name"] == "Tomato Pasta"
    assert "ingredients" in recipe
    assert "method" in recipe


def test_get_all_recipes_does_not_expose_user_id(client):
    response = client.get("/recipes")
    recipe = response.json()["recipes"][0]
    assert "userId" not in recipe
    assert "user_id" not in recipe


def test_get_recipe_by_id_returns_200(client):
    response = client.get("/recipes/recipe-1")
    assert response.status_code == 200


def test_get_recipe_by_id_returns_correct_recipe(client):
    response = client.get("/recipes/recipe-1")
    data = response.json()
    assert data["id"] == "recipe-1"
    assert data["name"] == "Tomato Pasta"


def test_get_recipe_by_id_does_not_expose_user_id(client):
    response = client.get("/recipes/recipe-1")
    assert "user_id" not in response.json()
    assert "userId" not in response.json()


def test_get_recipe_by_id_returns_404_when_not_found(client_404):
    response = client_404.get("/recipes/nonexistent")
    assert response.status_code == 404
