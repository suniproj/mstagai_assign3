from src.tools.budget import check_budget


def test_zero_semantics_are_converted_to_no_budget_before_budget_tool():
    """Budget tool receives None when the UI interprets $0 as any budget."""
    result = check_budget(
        [
            {
                "ingredient_line": "1 onion",
                "status": "available",
                "price": 5.0,
            }
        ],
        budget=None,
    )

    assert result["budget_status"] == "NO_BUDGET"
    assert result["estimated_total"] == 5.0


def test_over_budget_wins_even_when_some_prices_are_missing():
    """Known subtotal above budget is already enough to prove failure."""
    result = check_budget(
        [
            {
                "ingredient_line": "priced item",
                "status": "available",
                "price": 33.0,
            },
            {
                "ingredient_line": "unknown item",
                "status": "unavailable",
                "price": None,
            },
        ],
        budget=15.0,
    )

    assert result["budget_status"] == "OVER_BUDGET"
    assert result["estimated_total"] == 33.0
    assert len(result["pricing_errors"]) == 1


def test_incomplete_pricing_when_known_cost_is_within_hard_budget():
    """Missing prices make the true total unknown when a budget is specified."""
    result = check_budget(
        [
            {
                "ingredient_line": "priced item",
                "status": "available",
                "price": 10.0,
            },
            {
                "ingredient_line": "unknown item",
                "status": "unavailable",
                "price": None,
            },
        ],
        budget=50.0,
    )

    assert result["budget_status"] == "INCOMPLETE_PRICING"


def test_within_budget_requires_complete_pricing():
    """A hard budget is satisfied only when every price is known."""
    result = check_budget(
        [
            {
                "ingredient_line": "item one",
                "status": "available",
                "price": 10.0,
            },
            {
                "ingredient_line": "item two",
                "status": "available",
                "price": 5.0,
            },
        ],
        budget=20.0,
    )

    assert result["budget_status"] == "WITHIN_BUDGET"
