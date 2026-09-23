import json
from pathlib import Path

from mcp.server.mcpserver import MCPServer


PRICE_FILE = Path(
    "data/test_prices.json"
)

mcp = MCPServer(
    "meal-plan-price-server"
)


def load_price_catalog():
    """Load the synthetic grocery price catalog."""
    with open(PRICE_FILE) as file:
        return json.load(file)


@mcp.tool()
def lookup_grocery_price(
    ingredient_line: str,
) -> dict:
    """
    STEP 8 — Price MCP tool used by Agent 3.

    Look for a synthetic test price matching the ingredient line.
    If no price can be found, return an explicit unavailable result
    rather than inventing a price.
    """
    price_catalog = (
        load_price_catalog()
    )

    normalized_line = (
        ingredient_line.lower()
    )

    # Prefer longer ingredient names to reduce accidental partial matches.
    catalog_items = sorted(
        price_catalog.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    )

    for ingredient_name, price in catalog_items:
        if ingredient_name in normalized_line:
            return {
                "ingredient_line": ingredient_line,
                "matched_ingredient": ingredient_name,
                "status": "available",
                "price": float(price),
                "price_source": "synthetic_test_catalog",
            }

    return {
        "ingredient_line": ingredient_line,
        "matched_ingredient": None,
        "status": "unavailable",
        "price": None,
        "price_source": "synthetic_test_catalog",
    }


if __name__ == "__main__":
    mcp.run()