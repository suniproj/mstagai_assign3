from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
# switch to persistant memory
#from langgraph.checkpoint.memory import InMemorySaver
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
# for Agent 3
from src.agents.shopping_budget import (
    create_grocery_list,
    evaluate_budget,
    price_grocery_list,
)

from src.agents.meal_planner import (
    build_draft_meal_plan,
    retrieve_candidates,
)
from src.agents.nutrition_safety import validate_meal_plan
from src.state import MealPlanState


MAX_PLANNING_ATTEMPTS = 3


def agent1_retrieve(state):
    """STEP 3 — Agent 1 retrieves recipe candidates."""
    return retrieve_candidates(state)


def agent1_build_plan(state):
    """STEP 3 — Agent 1 builds the draft meal plan."""
    return build_draft_meal_plan(state)


def agent2_validate(state):
    """STEP 4 — Agent 2 independently validates the draft meal plan."""
    return validate_meal_plan(state)


def route_after_validation(state):
    """
    STEP 5-6 — Route based on Agent 2's validation result.

    PASS         -> meal-plan approval
    FAIL         -> Agent 1 revision path
    NEEDS_REVIEW -> human review
    """
    validation_status = state.get(
        "validation_status"
    )

    if validation_status == "FAIL":
        if state.get(
            "planning_attempts",
            0,
        ) >= MAX_PLANNING_ATTEMPTS:
            return "human_review"

        return "revise"

    if validation_status == "NEEDS_REVIEW":
        return "human_review"

    return "meal_plan_approval"


def revise_plan(state):
    """
    STEP 5 — Prepare Agent 1 to revise meals rejected by Agent 2.

    V1 records the failed recipe IDs so the next implementation can replace
    only those meal slots rather than rebuilding the entire plan.
    """
    failed_recipe_ids = {
        meal["recipe_id"]
        for meal in state.get(
            "meals_to_replace",
            []
        )
    }

    remaining_candidates = [
        recipe
        for recipe in state.get(
            "candidate_recipes",
            []
        )
        if recipe.get(
            "recipe_id"
        )
        not in failed_recipe_ids
    ]

    return {
        "candidate_recipes": remaining_candidates
    }


def human_review(state):
    """
    STEP 5 — Placeholder for the LangGraph human interrupt.

    V1 stops here. The next slice replaces this node with interrupt()
    and checkpoint persistence.
    """
    return {}


def meal_plan_approval(state):
    """
    STEP 6 — Pause so the human can review Agent 1's plan
    after Agent 2 has validated it.
    """
    decision = interrupt({
        "type": "meal_plan_approval",
        "message": "Review the validated meal plan.",
        "meal_plan": state.get("draft_meal_plan", []),
        "actions": [
            "approve",
            "modify",
            "more_info",
            "decline",
        ],
    })

    return {
        "meal_plan_approval": decision.get("action"),
        "meal_plan_feedback": decision.get("feedback"),
        "revision_request": decision.get("revision_request"),
    }


def route_after_meal_plan_approval(state):
    """STEP 6 — Route based on the human's meal-plan decision."""
    action = state.get("meal_plan_approval")

    if action == "modify":
        return "modify"

    if action == "more_info":
        return "more_info"

    if action == "decline":
        return "decline"

    return "approve"


def handle_modify(state):
    """STEP 6 — Modification will route back to Agent 1."""
    return {}


def handle_more_info(state):
    """STEP 6 — Placeholder for answering questions about the current plan."""
    return {}


def handle_decline(state):
    """STEP 6 — Stop when the user declines the plan."""
    return {
        "final_response": "Meal plan declined by user."
    }


def handle_approve(state):
    """STEP 6 — Meal plan approved; continue to Agent 3.""" 
    return {}


# Agent3 nodes
def agent3_build_grocery_list(state):
    """STEP 7 — Agent 3 builds the grocery list."""
    return create_grocery_list(state)


def agent3_price_groceries(state):
    """STEP 8 — Agent 3 gets prices through the Price MCP capability."""
    return price_grocery_list(state)


def agent3_check_budget(state):
    """STEP 9 — Agent 3 checks pricing completeness and budget."""
    return evaluate_budget(state)


# Budget Check
def route_after_budget_check(state):
    """
    STEP 9-10 — Decide whether the shopping plan can go to final approval.

    Complete pricing goes to final approval.
    Missing pricing or an over-budget plan requires human review.
    """
    budget_status = state.get(
        "budget_status"
    )

    if budget_status in {
        "INCOMPLETE_PRICING",
        "OVER_BUDGET",
    }:
        return "human_review"

    return "final_approval"

# 2nd HITL Node
def final_approval(state):
    """STEP 10 — Pause for human approval of the final shopping plan."""
    decision = interrupt({
        "type": "final_shopping_approval",
        "message": "Review the grocery list and estimated cost.",
        "estimated_total": state.get(
            "estimated_total"
        ),
        "budget_status": state.get(
            "budget_status"
        ),
        "pricing_errors": state.get(
            "pricing_errors",
            [],
        ),
        "actions": [
            "approve",
            "decline",
        ],
    })

    return {
        "final_approval": decision.get(
            "action"
        ),
        "final_feedback": decision.get(
            "feedback"
        ),
    }

# Final Routing
def route_after_final_approval(state):
    """STEP 10-11 — Finalize only when the human approves."""
    if state.get("final_approval") == "approve":
        return "finalize"

    return "decline"


def finalize_plan(state):
    """STEP 11 — Mark the validated and approved workflow complete."""
    return {
        "final_response": (
            "Meal plan and shopping plan approved."
        )
    }


def build_graph():
    """Build the Agent 1 -> Agent 2 validation/revision workflow."""
    graph = StateGraph(
        MealPlanState
    )

    graph.add_node(
        "agent1_retrieve",
        agent1_retrieve,
    )

    graph.add_node(
        "agent1_build_plan",
        agent1_build_plan,
    )

    graph.add_node(
        "agent2_validate",
        agent2_validate,
    )

    graph.add_node(
        "revise_plan",
        revise_plan,
    )

    graph.add_node(
        "human_review",
        human_review,
    )

    graph.add_node(
        "meal_plan_approval",
        meal_plan_approval,
    )

    graph.add_node(
        "handle_modify", 
        handle_modify,
    )

    graph.add_node(
        "handle_more_info", 
        handle_more_info,
    )

    graph.add_node(
        "handle_decline", 
        handle_decline,
    )

    graph.add_node(
        "handle_approve", 
        handle_approve,
    )

    graph.add_node(
        "agent3_build_grocery_list",
        agent3_build_grocery_list,
    )

    graph.add_node(
        "agent3_price_groceries",
        agent3_price_groceries,
    )

    graph.add_node(
        "agent3_check_budget",
        agent3_check_budget,
    )

    graph.add_node(
        "final_approval",
        final_approval,
    )

    graph.add_node(
        "finalize_plan",
        finalize_plan,
    )

    # STEP 3 — Agent 1 retrieval and planning.
    graph.add_edge(
        START,
        "agent1_retrieve",
    )

    graph.add_edge(
        "agent1_retrieve",
        "agent1_build_plan",
    )

    # STEP 4 — Agent 2 independently validates Agent 1's draft.
    graph.add_edge(
        "agent1_build_plan",
        "agent2_validate",
    )

    # STEP 5-6 — PASS, FAIL, and NEEDS_REVIEW take different routes.
    graph.add_conditional_edges(
        "agent2_validate",
        route_after_validation,
        {
            "revise": "revise_plan",
            "human_review": "human_review",
            "meal_plan_approval": "meal_plan_approval",
        },
    )

    # Failed recipes are removed and Agent 1 rebuilds the plan.
    graph.add_edge(
        "revise_plan",
        "agent1_build_plan",
    )

    graph.add_edge(
        "human_review",
        END,
    )

    graph.add_conditional_edges(
        "meal_plan_approval",
        route_after_meal_plan_approval,
        {
            "modify": "handle_modify",
            "more_info": "handle_more_info",
            "decline": "handle_decline",
            "approve": "handle_approve",
        },
    )

    graph.add_edge(
        "handle_modify", 
        END)

    graph.add_edge(
        "handle_more_info",
        END)

    graph.add_edge(
        "handle_decline", 
        END)

    # STEP 7-9 — Approved meal plans move to Agent 3.
    graph.add_edge(
        "handle_approve",
        "agent3_build_grocery_list",
    )

    graph.add_edge(
        "agent3_build_grocery_list",
        "agent3_price_groceries",
    )

    graph.add_edge(
        "agent3_price_groceries",
        "agent3_check_budget",
    )

    graph.add_conditional_edges(
        "agent3_check_budget",
        route_after_budget_check,
        {
            "human_review": "human_review",
            "final_approval": "final_approval",
        },
    )

    graph.add_conditional_edges(
        "final_approval",
        route_after_final_approval,
        {
            "finalize": "finalize_plan",
            "decline": "handle_decline",
        },
    )

    graph.add_edge(
        "finalize_plan",
        END,
    )

    # Persist graph checkpoints so HITL workflows survive process restarts.
    checkpoint_connection = sqlite3.connect(
        "data/meal_plan_checkpoints.db",
        check_same_thread=False,
    )

    checkpointer = SqliteSaver(
        checkpoint_connection
    )

    return graph.compile(
        checkpointer=checkpointer
    )

meal_plan_graph = build_graph()

