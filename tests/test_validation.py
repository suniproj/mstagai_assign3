from src.tools.constraint_validator import validate_recipe


def test_explicit_vegan_pass():
    recipe = {
        "recipe_id": "test-1",
        "recipe_name": "Bean Chili",
        "health_labels": ["Vegan", "Soy-Free"],
        "meal_type": ["lunch/dinner"],
        "protein_per_serving": 19.0,
        "ingredients": [
            "black beans",
            "tomatoes",
        ],
    }

    requirements = {
        "diet": "Vegan",
        "meal_type": "lunch/dinner",
        "min_protein": 15,
        "excluded_ingredients": ["soy"],
    }

    result = validate_recipe(
        recipe,
        requirements,
    )

    assert result["status"] == "PASS"


def test_literal_excluded_ingredient_fails():
    recipe = {
        "recipe_id": "test-2",
        "recipe_name": "Vegetable Noodle Bowl",
        "health_labels": ["Vegan"],
        "meal_type": ["lunch/dinner"],
        "protein_per_serving": 15.7,
        "ingredients": [
            "rice noodles",
            "carrot",
            "soy sauce",
        ],
    }

    requirements = {
        "diet": "Vegan",
        "meal_type": "lunch/dinner",
        "min_protein": 15,
        "excluded_ingredients": ["soy"],
    }

    result = validate_recipe(
        recipe,
        requirements,
    )

    assert result["status"] == "FAIL"


def test_low_protein_fails():
    recipe = {
        "recipe_id": "test-3",
        "recipe_name": "Vegetable Couscous",
        "health_labels": ["Vegan"],
        "meal_type": ["lunch/dinner"],
        "protein_per_serving": 11.8,
        "ingredients": [
            "couscous",
            "zucchini",
        ],
    }

    requirements = {
        "diet": "Vegan",
        "meal_type": "lunch/dinner",
        "min_protein": 15,
        "excluded_ingredients": [],
    }

    result = validate_recipe(
        recipe,
        requirements,
    )

    assert result["status"] == "FAIL"


def test_missing_protein_needs_review():
    recipe = {
        "recipe_id": "test-4",
        "recipe_name": "Unknown Soup",
        "health_labels": ["Vegan"],
        "meal_type": ["lunch/dinner"],
        "protein_per_serving": None,
        "ingredients": [
            "vegetables",
            "broth",
        ],
    }

    requirements = {
        "diet": "Vegan",
        "meal_type": "lunch/dinner",
        "min_protein": 15,
        "excluded_ingredients": [],
    }

    result = validate_recipe(
        recipe,
        requirements,
    )

    assert result["status"] == "NEEDS_REVIEW"
