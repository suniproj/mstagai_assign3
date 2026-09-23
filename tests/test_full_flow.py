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
        -> explicit budget/pricing outcome
    """

    # Use a unique thread so persisted checkpoints from earlier
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
    # LangGraph then pauses for human meal-plan review.
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
        paused_result["plan_status"]
        == "COMPLETE"
    )

    assert (
        paused_result["validation_status"]
        == "PASS"
    )

    assert len(
        paused_result["draft_meal_plan"]
    ) == 3

    # STEP 6 — Simulate human approval.
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

    budget_status = shopping_result.get(
        "budget_status"
    )

    assert budget_status in {
        "WITHIN_BUDGET",
        "OVER_BUDGET",
        "INCOMPLETE_PRICING",
        "NO_BUDGET",
    }

    # Agent 3 must always return an explicit next state.
    shopping_interrupts = (
        shopping_result.get(
            "__interrupt__"
        )
    )

    assert shopping_interrupts

    interrupt_type = (
        shopping_interrupts[0].value[
            "type"
        ]
    )

    # STEP 9-10 — Verify that the interrupt agrees with
    # Agent 3's budget result.
    if budget_status == "WITHIN_BUDGET":
        assert (
            interrupt_type
            == "shopping_review"
        )

    elif budget_status == "NO_BUDGET":
        assert (
            interrupt_type
            == "shopping_review"
        )

    elif budget_status == "OVER_BUDGET":
        assert (
            interrupt_type
            == "budget_failure"
        )

    elif (
        budget_status
        == "INCOMPLETE_PRICING"
    ):
        assert (
            interrupt_type
            == "pricing_unknown"
        )