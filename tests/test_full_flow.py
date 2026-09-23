from uuid import uuid4

from langgraph.types import Command

from src.graph import meal_plan_graph


def test_full_agent_flow_to_agent3():
    """
    Integration test:

    Agent 1
        -> Agent 2
        -> HITL meal-plan approval
        -> Agent 3
        -> Price MCP
        -> budget/pricing decision
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

    # STEP 3-6 — Agent 1 builds the plan, Agent 2 validates it,
    # then LangGraph pauses for human meal-plan approval.
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
        == "meal_plan_approval"
    )

    assert (
        paused_result["validation_status"]
        == "PASS"
    )

    # STEP 6 — Simulate the human approving the meal plan.
    agent3_result = meal_plan_graph.invoke(
        Command(
            resume={
                "action": "approve",
                "feedback": None,
            }
        ),
        config=config,
    )

    # STEP 7-9 — Agent 3 should have built and priced a grocery list.
    assert agent3_result.get(
        "grocery_list"
    )

    assert agent3_result.get(
        "priced_grocery_list"
    )

    assert agent3_result.get(
        "budget_status"
    ) in {
        "WITHIN_BUDGET",
        "OVER_BUDGET",
        "INCOMPLETE_PRICING",
        "NO_BUDGET",
    }

    print()
    print(
        "Budget status:",
        agent3_result.get(
            "budget_status"
        ),
    )

    print(
        "Known subtotal:",
        agent3_result.get(
            "estimated_total"
        ),
    )

    print(
        "Pricing errors:",
        len(
            agent3_result.get(
                "pricing_errors",
                [],
            )
        ),
    )

    print(
        "Next interrupt:",
        agent3_result.get(
            "__interrupt__"
        ),
    )

