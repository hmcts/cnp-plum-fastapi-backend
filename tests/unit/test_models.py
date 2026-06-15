from app.models import Recipe, RecipeResponse


def test_recipe_response_excludes_user_id():
    recipe = Recipe(id="1", user_id="u1", name="Pasta", ingredients="pasta", method="boil")
    response = RecipeResponse.model_validate(recipe, from_attributes=True)
    response_dict = response.model_dump()
    assert "user_id" not in response_dict
    assert "userId" not in response_dict


def test_recipe_response_includes_required_fields():
    recipe = Recipe(id="1", user_id="u1", name="Pasta", ingredients="pasta", method="boil")
    response = RecipeResponse.model_validate(recipe, from_attributes=True)
    assert response.id == "1"
    assert response.name == "Pasta"
    assert response.ingredients == "pasta"
    assert response.method == "boil"
