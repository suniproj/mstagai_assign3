from src.mcp_clients.recipe_client import search_recipe_tool

def retrieve_candidates(state):
    """STEP 3 — Agent 1 retrieves candidates for each requested meal type."""
    candidate_recipes = []
    diet = state.get("diet")
    min_protein = state.get("min_protein_per_meal")
    meal_types = state.get("meal_types", ["lunch/dinner"])

    for meal_type in meal_types:
        query = f"{diet or ''} {meal_type} meal".strip()
        recipes = search_recipe_tool(
            query=query,
            diet=diet,
            meal_type=meal_type,
            min_protein=min_protein,
            top_k=5,
        )
        for recipe in recipes:
            recipe["requested_meal_type"] = meal_type
        candidate_recipes.extend(recipes)

    return {
        "candidate_recipes": candidate_recipes,
        "planning_attempts": state.get("planning_attempts", 0) + 1,
    }
