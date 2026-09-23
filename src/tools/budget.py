def check_budget(priced_items, budget):
    """STEP 9 — Calculate known costs and determine budget status."""
    available_items = [
        item
        for item in priced_items
        if item["status"] == "available"
    ]

    unavailable_items = [
        item
        for item in priced_items
        if item["status"] == "unavailable"
    ]

    known_subtotal = round(
        sum(
            item["price"]
            for item in available_items
        ),
        2,
    )

    if unavailable_items:
        return {
            "estimated_total": known_subtotal,
            "budget_status": "INCOMPLETE_PRICING",
            "pricing_errors": [
                (
                    "Price unavailable for "
                    f"{item['ingredient_line']}"
                )
                for item in unavailable_items
            ],
        }

    if budget is None:
        return {
            "estimated_total": known_subtotal,
            "budget_status": "NO_BUDGET",
            "pricing_errors": [],
        }

    if known_subtotal <= budget:
        budget_status = "WITHIN_BUDGET"
    else:
        budget_status = "OVER_BUDGET"

    return {
        "estimated_total": known_subtotal,
        "budget_status": budget_status,
        "pricing_errors": [],
    }


