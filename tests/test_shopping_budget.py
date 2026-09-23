from src.tools.budget import check_budget


def test_within_budget():
    items = [
        {
            "status": "available",
            "price": 10.0,
        },
        {
            "status": "available",
            "price": 5.0,
        },
    ]

    result = check_budget(
        items,
        budget=20,
    )

    assert result["estimated_total"] == 15.0
    assert result["budget_status"] == "WITHIN_BUDGET"


def test_over_budget():
    items = [
        {
            "status": "available",
            "price": 15.0,
        },
        {
            "status": "available",
            "price": 10.0,
        },
    ]

    result = check_budget(
        items,
        budget=20,
    )

    assert result["budget_status"] == "OVER_BUDGET"


def test_incomplete_pricing():
    items = [
        {
            "ingredient_line": "1 onion",
            "status": "available",
            "price": 1.49,
        },
        {
            "ingredient_line": "special ingredient",
            "status": "unavailable",
            "price": None,
        },
    ]

    result = check_budget(
        items,
        budget=20,
    )

    assert (
        result["budget_status"]
        == "INCOMPLETE_PRICING"
    )

    assert len(
        result["pricing_errors"]
    ) == 1


