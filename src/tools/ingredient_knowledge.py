# Known ingredient relationships used by Agent 2 for safety validation.
INGREDIENT_GROUPS = {
    "soy": {
        "soy",
        "soy sauce",
        "tofu",
        "miso",
        "edamame",
        "tempeh",
    },
    "mushroom": {
        "mushroom",
        "mushrooms",
        "shiitake",
        "cremini",
        "portobello",
    },
}


AMBIGUOUS_TERMS = {
    "dairy": {
        "creamy dressing",
        "cream-style sauce",
    },
}


def find_related_exclusion(recipe, excluded_ingredient):
    """
    STEP 4 — Agent 2 checks semantic ingredient relationships.

    Returns FAIL for known conflicts, NEEDS_REVIEW for ambiguous evidence,
    and PASS when no conflict is found.
    """
    ingredients = [
        ingredient.lower()
        for ingredient in recipe.get("ingredients", [])
    ]

    ingredient_text = " ".join(ingredients)
    excluded_value = excluded_ingredient.lower()

    related_terms = INGREDIENT_GROUPS.get(
        excluded_value,
        {excluded_value},
    )

    for related_term in related_terms:
        if related_term in ingredient_text:
            return {
                "status": "FAIL",
                "constraint": excluded_ingredient,
                "evidence": related_term,
                "message": (
                    f"Ingredient '{related_term}' conflicts with "
                    f"the exclusion '{excluded_ingredient}'."
                ),
            }

    ambiguous_terms = AMBIGUOUS_TERMS.get(
        excluded_value,
        set(),
    )

    for ambiguous_term in ambiguous_terms:
        if ambiguous_term in ingredient_text:
            return {
                "status": "NEEDS_REVIEW",
                "constraint": excluded_ingredient,
                "evidence": ambiguous_term,
                "message": (
                    f"Ingredient '{ambiguous_term}' may conflict with "
                    f"'{excluded_ingredient}', but the available evidence "
                    f"is insufficient to verify it."
                ),
            }

    return {
        "status": "PASS",
        "constraint": excluded_ingredient,
        "evidence": None,
        "message": "No conflicting ingredient evidence found.",
    }

