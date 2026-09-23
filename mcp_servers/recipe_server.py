from mcp.server.mcpserver import MCPServer

from src.recipe_repository import search_recipes


mcp = MCPServer(
    "meal-plan-recipe-server"
)


@mcp.tool()
def search_recipe_knowledge_base(
    query: str,
    diet: str | None = None,
    meal_type: str | None = None,
    min_protein: float | None = None,
    top_k: int = 5,
) -> list[dict]:
    """
    STEP 3 — Recipe MCP tool used by Agent 1.

    Search the Assignment 2 Pinecone recipe knowledge base and return
    structured recipe candidates.

    Exact dietary, meal-type, and protein constraints are applied through
    Pinecone metadata filtering before semantic similarity ranking.
    """
    return search_recipes(
        query=query,
        diet=diet,
        meal_type=meal_type,
        min_protein=min_protein,
        top_k=top_k,
    )


if __name__ == "__main__":
    mcp.run()