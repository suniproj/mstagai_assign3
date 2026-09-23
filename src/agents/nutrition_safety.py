from src.tools.constraint_validator import validate_recipe
from src.tools.ingredient_knowledge import find_related_exclusion


def validate_recipe_with_agent2(recipe, requirements):
    """
    STEP 4 — Agent 2 independently validates one recipe.

    Deterministic checks run first. Semantic ingredient relationships
    are checked only for exclusions not already caught literally.
    """
    deterministic_result = validate_recipe(
        recipe,
        requirements,
    )

    violations = list(
        deterministic_result["violations"]
    )

    semantic_results = []

    for excluded_ingredient in requirements.get(
        "excluded_ingredients",
        [],
    ):
        semantic_result = find_related_exclusion(
            recipe,
            excluded_ingredient,
        )

        semantic_results.append(
            semantic_result
        )

    semantic_failures = [
        result
        for result in semantic_results
        if result["status"] == "FAIL"
    ]

    semantic_reviews = [
        result
        for result in semantic_results
        if result["status"] == "NEEDS_REVIEW"
    ]

    if violations or semantic_failures:
        status = "FAIL"

    elif semantic_reviews:
        status = "NEEDS_REVIEW"

    else:
        status = "PASS"

    return {
        "recipe_id": recipe.get("recipe_id"),
        "recipe_name": recipe.get("recipe_name"),
        "status": status,
        "deterministic_violations": violations,
        "semantic_checks": semantic_results,
    }

def validate_meal_plan(state):
    """
    STEP 4 — Agent 2 independently validates every meal in the draft plan.

    Returns PASS only when every meal passes. FAIL identifies the exact
    meal slots Agent 1 must replace. NEEDS_REVIEW triggers human review.
    """
    draft_meal_plan = state.get("draft_meal_plan", [])

    requirements = {
        "diet": state.get("diet"),
        "min_protein": state.get("min_protein_per_meal"),
        "excluded_ingredients": state.get("excluded_ingredients", []),
    }

    validation_results = []
    meals_to_replace = []
    needs_review = False

    for meal in draft_meal_plan:
        recipe = meal["recipe"]

        # Validate against the dataset category appropriate for this slot.
        meal_requirements = dict(requirements)
        meal_requirements["meal_type"] = meal["dataset_meal_type"]

        result = validate_recipe_with_agent2(
            recipe,
            meal_requirements,
        )

        result["day"] = meal["day"]
        result["meal_slot"] = meal["meal_slot"]

        validation_results.append(result)

        if result["status"] == "FAIL":
            meals_to_replace.append({
                "day": meal["day"],
                "meal_slot": meal["meal_slot"],
                "recipe_id": recipe["recipe_id"],
                "recipe_name": recipe["recipe_name"],
            })

        elif result["status"] == "NEEDS_REVIEW":
            needs_review = True

    # FAIL takes priority because known violations must be corrected first.
    if meals_to_replace:
        overall_status = "FAIL"
    elif needs_review:
        overall_status = "NEEDS_REVIEW"
    else:
        overall_status = "PASS"

    return {
        "validation_status": overall_status,
        "validation_violations": validation_results,
        "meals_to_replace": meals_to_replace,
    }


