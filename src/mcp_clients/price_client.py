from mcp_servers.price_server import lookup_grocery_price


def lookup_price_tool(ingredient_line):
    """
    STEP 8 — V1 adapter to the same capability exposed by Price MCP.

    A transport-based MCP client can replace this adapter later without
    changing Agent 3's workflow.
    """
    return lookup_grocery_price(
        ingredient_line
    )

