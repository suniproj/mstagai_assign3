from src.recipe_repository import search_recipes

def search_recipe_tool(query, diet=None, meal_type=None, min_protein=None, top_k=5):
    """STEP 3 — V1 adapter to the same capability exposed by Recipe MCP."""
    return search_recipes(query, diet, meal_type, min_protein, top_k)
