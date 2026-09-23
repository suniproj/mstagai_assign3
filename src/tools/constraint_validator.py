def validate_diet(recipe, required_diet):
    """STEP 4 — Check an explicit diet requirement against recipe metadata."""
    if not required_diet:
        return []

    health_labels = recipe.get("health_labels", [])

    if required_diet in health_labels:
        return []

    return [{
        "constraint": "diet",
        "expected": required_diet,
        "evidence": health_labels,
        "message": f"Recipe is not explicitly labeled {required_diet}.",
    }]


def validate_meal_type(recipe, required_meal_type):
    """STEP 4 — Check that the recipe matches the requested meal type."""
    if not required_meal_type:
        return []

    meal_types = recipe.get("meal_type", [])

    if required_meal_type in meal_types:
        return []

    return [{
        "constraint": "meal_type",
        "expected": required_meal_type,
        "evidence": meal_types,
        "message": f"Recipe is not labeled {required_meal_type}.",
    }]


def validate_protein(recipe, min_protein):
    """STEP 4 — Check the minimum protein requirement."""
    if min_protein is None:
        return []

    protein = recipe.get("protein_per_serving")

    if protein is None:
        return [{
            "constraint": "protein",
            "expected": min_protein,
            "evidence": None,
            "message": "Protein information is unavailable.",
            "needs_review": True,
        }]

    if protein >= min_protein:
        return []

    return [{
        "constraint": "protein",
        "expected": min_protein,
        "evidence": protein,
        "message": (
            f"Recipe has {protein}g protein per serving; "
            f"minimum is {min_protein}g."
        ),
    }]


def validate_literal_exclusions(recipe, excluded_ingredients):
    """
    STEP 4 — Detect exclusions that appear literally in ingredient text.

    Semantic relationships such as tofu -> soy or shiitake -> mushroom
    are intentionally left for Agent 2 reasoning.
    """
    violations = []

    ingredients = recipe.get("ingredients", [])
    ingredient_text = " ".join(ingredients).lower()

    for excluded_ingredient in excluded_ingredients:
        excluded_value = excluded_ingredient.lower()

        if excluded_value in ingredient_text:
            violations.append({
                "constraint": "excluded_ingredient",
                "expected": f"exclude {excluded_ingredient}",
                "evidence": ingredient_text,
                "message": (
                    f"Ingredient evidence contains "
                    f"'{excluded_ingredient}'."
                ),
            })

    return violations


def validate_recipe(recipe, requirements):
    """Run all deterministic Agent 2 checks for one recipe."""
    violations = []

    violations.extend(
        validate_diet(
            recipe,
            requirements.get("diet"),
        )
    )

    violations.extend(
        validate_meal_type(
            recipe,
            requirements.get("meal_type"),
        )
    )

    violations.extend(
        validate_protein(
            recipe,
            requirements.get("min_protein"),
        )
    )

    violations.extend(
        validate_literal_exclusions(
            recipe,
            requirements.get("excluded_ingredients", []),
        )
    )

    if any(
        violation.get("needs_review")
        for violation in violations
    ):
        status = "NEEDS_REVIEW"
    elif violations:
        status = "FAIL"
    else:
        status = "PASS"

    return {
        "recipe_id": recipe.get("recipe_id"),
        "recipe_name": recipe.get("recipe_name"),
        "status": status,
        "violations": violations,
    }
