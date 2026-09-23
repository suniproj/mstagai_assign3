from uuid import uuid4

from langgraph.types import Command

from src.graph import meal_plan_graph


def test_full_agent_flow_to_agent3():
    """
    Integration test:

    Agent 1
        -> Agent 2
        -> HITL meal-plan review
        -> human approval
        -> Agent 3
        -> Price MCP
        -> shopping/budget review
    """

    # Use a unique thread so persisted SQLite checkpoints from earlier
    # test runs cannot interfere with this test.
    thread_id = (
        f"test-full-flow-{uuid4()}"
    )

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    initial_state = {
        "days": 1,
        "meal_slots": [
            "breakfast",
            "lunch",
            "dinner",
        ],
        "diet": "Vegan",
        "budget": 75,
    }

    # STEP 3-6 — Agent 1 builds the plan and Agent 2 validates it.
    # LangGraph then pauses so the human can review each recipe.
    paused_result = meal_plan_graph.invoke(
        initial_state,
        config=config,
    )

    interrupts = paused_result.get(
        "__interrupt__"
    )

    assert interrupts

    assert (
        interrupts[0].value["type"]
        == "meal_plan_review"
    )

    assert (
        paused_result["validation_status"]
        == "PASS"
    )

    assert len(
        paused_result["draft_meal_plan"]
    ) == 3

    # STEP 6 — Simulate the human accepting all three recipes.
    shopping_result = meal_plan_graph.invoke(
        Command(
            resume={
                "action": "approve",
                "feedback": None,
            }
        ),
        config=config,
    )

    # STEP 7-9 — Agent 3 should build and price the grocery list.
    assert shopping_result.get(
        "grocery_list"
    )

    assert shopping_result.get(
        "priced_grocery_list"
    )

    assert shopping_result.get(
        "budget_status"
    ) in {
        "WITHIN_BUDGET",
        "OVER_BUDGET",
        "INCOMPLETE_PRICING",
        "NO_BUDGET",
    }

    # STEP 10 — The graph should pause again for shopping review.
    shopping_interrupts = (
        shopping_result.get(
            "__interrupt__"
        )
    )

    assert shopping_interrupts

    assert (
        shopping_interrupts[0].value[
            "type"
        ]
        == "shopping_review"
    )