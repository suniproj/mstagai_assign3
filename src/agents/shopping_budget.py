from src.mcp_clients.price_client import lookup_price_tool
from src.tools.budget import check_budget
from src.tools.grocery_list import build_grocery_list


def create_grocery_list(state):
    """STEP 7 — Agent 3 builds the grocery list from the approved meal plan."""
    grocery_list = build_grocery_list(
        state.get(
            "draft_meal_plan",
            [],
        )
    )

    return {
        "grocery_list": grocery_list
    }


def price_grocery_list(state):
    """STEP 8 — Agent 3 uses the Price MCP capability for each grocery item."""
    priced_items = []

    for grocery_item in state.get(
        "grocery_list",
        [],
    ):
        price_result = lookup_price_tool(
            grocery_item[
                "ingredient_line"
            ]
        )

        priced_items.append({
            **grocery_item,
            **price_result,
        })

    return {
        "priced_grocery_list": priced_items
    }


def evaluate_budget(state):
    """STEP 9 — Agent 3 checks the known grocery cost against the budget."""
    return check_budget(
        state.get(
            "priced_grocery_list",
            [],
        ),
        state.get("budget"),
    )


