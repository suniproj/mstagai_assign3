from mcp.server.fastmcp import FastMCP
from src.recipe_repository import search_recipes

mcp = FastMCP("meal-plan-recipe-server")

@mcp.tool()
def search_recipe_knowledge_base(
    query: str,
    diet: str | None = None,
    meal_type: str | None = None,
    min_protein: float | None = None,
    top_k: int = 5,
) -> list[dict]:
    """STEP 3 — Recipe MCP tool used by Agent 1."""
    return search_recipes(query, diet, meal_type, min_protein, top_k)

if __name__ == "__main__":
    mcp.run()
