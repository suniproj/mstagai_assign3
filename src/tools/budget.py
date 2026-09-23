def check_budget(priced_items, budget):
    """
    STEP 9 — Calculate known cost and classify the budget outcome.

    Budget semantics:
    - None means the user selected any budget.
    - A positive budget is a hard constraint.
    - Input validation prevents nonzero budgets below $3.
    """
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

    # With no budget constraint, incomplete prices do not prevent reporting
    # the known subtotal. The UI still shows unavailable items explicitly.
    if budget is None:
        return {
            "estimated_total": known_subtotal,
            "budget_status": "NO_BUDGET",
            "pricing_errors": [
                (
                    "Price unavailable for "
                    f"{item['ingredient_line']}"
                )
                for item in unavailable_items
            ],
        }

    # If known cost alone exceeds the hard budget, the budget is already
    # unsatisfied even if additional prices are unavailable.
    if known_subtotal > budget:
        return {
            "estimated_total": known_subtotal,
            "budget_status": "OVER_BUDGET",
            "pricing_errors": [
                (
                    "Price unavailable for "
                    f"{item['ingredient_line']}"
                )
                for item in unavailable_items
            ],
        }

    # Known cost is within budget, but missing prices mean the true total
    # cannot be verified against the user's hard budget.
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

    return {
        "estimated_total": known_subtotal,
        "budget_status": "WITHIN_BUDGET",
        "pricing_errors": [],
    }
