import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from src.agents.meal_planner import (
    build_draft_meal_plan,
    replace_requested_meal,
    retrieve_candidates,
)
from src.agents.nutrition_safety import validate_meal_plan
from src.agents.shopping_budget import (
    create_grocery_list,
    evaluate_budget,
    price_grocery_list,
)
from src.state import MealPlanState


MAX_PLANNING_ATTEMPTS = 3


def agent1_retrieve(state):
    """STEP 3 — Agent 1 retrieves recipe candidates."""
    return retrieve_candidates(state)


def agent1_build_plan(state):
    """STEP 3 — Agent 1 builds and assesses plan completeness."""
    return build_draft_meal_plan(state)


def route_after_plan_build(state):
    """STEP 3 — Never send an incomplete plan to normal validation/approval."""
    if state.get("plan_status") != "COMPLETE":
        return "planning_failure"

    return "validate"


def planning_failure(state):
    """STEP 3 — Pause with an explicit unsatisfied-request outcome."""
    decision = interrupt({
        "type": "planning_failure",
        "message": state.get(
            "planning_message",
            "The requested plan could not be completed.",
        ),
        "missing_meal_slots": state.get("missing_meal_slots", []),
        "actions": ["modify_settings", "cancel"],
    })

    return {
        "meal_plan_approval": decision.get("action"),
    }


def route_after_planning_failure(state):
    """STEP 3 — Human either changes requirements or abandons the request."""
    if state.get("meal_plan_approval") == "modify_settings":
        return "modify_settings"

    return "cancel"


def wait_for_settings_change(state):
    """
    STEP 3 — End this graph invocation after requesting modified settings.

    Streamlit starts a fresh thread with the edited requirements.
    """
    return {
        "final_response": "Modify the settings and create the meal plan again."
    }


def agent1_replace_meal(state):
    """STEP 6/10 — Agent 1 replaces one selected meal."""
    return replace_requested_meal(state)


def route_after_replacement(state):
    """STEP 6/10 — Replacement failure must be explicit."""
    if state.get("plan_status") == "REPLACEMENT_FAILED":
        return "replacement_failure"

    return "validate"


def replacement_failure(state):
    """STEP 6/10 — Pause when no suitable alternative recipe exists."""
    decision = interrupt({
        "type": "replacement_failure",
        "message": state.get(
            "planning_message",
            "No suitable replacement recipe was found.",
        ),
        "actions": [
            "keep_current",
            "modify_settings",
            "cancel",
        ],
    })

    return {
        "meal_plan_approval": decision.get("action"),
    }


def route_after_replacement_failure(state):
    action = state.get("meal_plan_approval")

    if action == "keep_current":
        return "meal_plan_review"

    if action == "modify_settings":
        return "modify_settings"

    return "cancel"


def agent2_validate(state):
    """STEP 4 — Agent 2 independently validates the complete plan."""
    return validate_meal_plan(state)


def route_after_validation(state):
    """STEP 5 — Route Agent 2 PASS, FAIL, and NEEDS_REVIEW outcomes."""
    status = state.get("validation_status")

    if status == "FAIL":
        if state.get("planning_attempts", 0) >= MAX_PLANNING_ATTEMPTS:
            return "human_review"

        return "revise"

    if status == "NEEDS_REVIEW":
        return "human_review"

    return "meal_plan_review"


def revise_plan(state):
    """STEP 5 — Remove recipes rejected by Agent 2 before rebuilding."""
    failed_ids = {
        meal["recipe_id"]
        for meal in state.get("meals_to_replace", [])
    }

    return {
        "candidate_recipes": [
            recipe
            for recipe in state.get("candidate_recipes", [])
            if recipe.get("recipe_id") not in failed_ids
        ]
    }


def human_review(state):
    """STEP 5 — Return an explicit unresolved-safety outcome."""
    return {
        "final_response": (
            "Human review is required because the available recipe evidence "
            "is not sufficient to continue safely."
        )
    }


def meal_plan_review(state):
    """STEP 6 — Human approves or replaces a specific recipe."""
    decision = interrupt({
        "type": "meal_plan_review",
        "meal_plan": state.get("draft_meal_plan", []),
        "actions": ["approve", "replace", "decline"],
    })

    return {
        "meal_plan_approval": decision.get("action"),
        "meal_plan_feedback": decision.get("feedback"),
        "revision_request": decision.get("revision_request"),
    }


def route_after_meal_plan_review(state):
    action = state.get("meal_plan_approval")

    if action == "replace":
        return "replace"

    if action == "decline":
        return "cancel"

    return "approve"


def handle_cancel(state):
    """Return a clear cancellation outcome."""
    return {"final_response": "Current meal-planning request was cancelled."}


def handle_meal_plan_approval(state):
    """STEP 6 — Approved plan proceeds to Agent 3."""
    return {}


def agent3_build_grocery_list(state):
    """STEP 7 — Agent 3 builds the grocery list."""
    return create_grocery_list(state)


def agent3_price_groceries(state):
    """STEP 8 — Agent 3 prices groceries."""
    return price_grocery_list(state)


def agent3_check_budget(state):
    """STEP 9 — Agent 3 evaluates pricing completeness and budget."""
    return evaluate_budget(state)


def route_after_budget_result(state):
    """STEP 9 — Treat user-supplied budget as a real workflow constraint."""
    status = state.get("budget_status")

    if status == "OVER_BUDGET":
        return "budget_failure"

    if status == "INCOMPLETE_PRICING":
        return "pricing_unknown"

    return "shopping_review"


def budget_failure(state):
    """STEP 9 — Pause because the known subtotal already exceeds the budget."""
    budget = state.get("budget")
    subtotal = state.get("estimated_total", 0)

    decision = interrupt({
        "type": "budget_failure",
        "message": (
            f"The current plan does not meet the ${budget:.2f} budget. "
            f"The known subtotal is ${subtotal:.2f}."
        ),
        "budget": budget,
        "estimated_total": subtotal,
        "over_by": round(subtotal - budget, 2),
        "actions": [
            "try_cheaper_meal",
            "modify_settings",
            "cancel",
        ],
    })

    return {
        "shopping_review_action": decision.get("action"),
        "revision_request": decision.get("revision_request"),
    }


def route_after_budget_failure(state):
    action = state.get("shopping_review_action")

    if action == "try_cheaper_meal":
        return "replace_for_cost"

    if action == "modify_settings":
        return "modify_settings"

    return "cancel"


def pricing_unknown(state):
    """STEP 9 — Pause because missing prices prevent budget verification."""
    decision = interrupt({
        "type": "pricing_unknown",
        "message": (
            "Some grocery prices are unavailable, so the requested budget "
            "cannot be verified."
        ),
        "budget": state.get("budget"),
        "estimated_total": state.get("estimated_total"),
        "pricing_errors": state.get("pricing_errors", []),
        "actions": [
            "continue_partial",
            "modify_settings",
            "cancel",
        ],
    })

    return {
        "shopping_review_action": decision.get("action"),
    }


def route_after_pricing_unknown(state):
    action = state.get("shopping_review_action")

    if action == "continue_partial":
        return "shopping_review"

    if action == "modify_settings":
        return "modify_settings"

    return "cancel"


def shopping_review(state):
    """STEP 10 — Human reviews complete or incomplete pricing explicitly."""
    decision = interrupt({
        "type": "shopping_review",
        "estimated_total": state.get("estimated_total"),
        "budget_status": state.get("budget_status"),
        "pricing_errors": state.get("pricing_errors", []),
        "meal_plan": state.get("draft_meal_plan", []),
        "actions": ["approve", "find_cheaper_meal", "decline"],
    })

    return {
        "shopping_review_action": decision.get("action"),
        "revision_request": decision.get("revision_request"),
    }


def route_after_shopping_review(state):
    action = state.get("shopping_review_action")

    if action == "find_cheaper_meal":
        return "replace_for_cost"

    if action == "decline":
        return "cancel"

    return "finalize"


def prepare_cost_revision(state):
    """STEP 10 — Mark the selected replacement as cost-driven."""
    request = dict(state.get("revision_request") or {})
    request["reason"] = "cost"

    if not request.get("feedback"):
        request["feedback"] = "cheaper alternative"

    return {"revision_request": request}


def finalize_plan(state):
    """STEP 11 — Final approved output."""
    return {
        "final_approval": "approve",
        "final_response": "Meal plan and shopping plan approved.",
    }


def build_graph():
    graph = StateGraph(MealPlanState)

    graph.add_node("agent1_retrieve", agent1_retrieve)
    graph.add_node("agent1_build_plan", agent1_build_plan)
    graph.add_node("planning_failure", planning_failure)
    graph.add_node("wait_for_settings_change", wait_for_settings_change)
    graph.add_node("agent1_replace_meal", agent1_replace_meal)
    graph.add_node("replacement_failure", replacement_failure)
    graph.add_node("agent2_validate", agent2_validate)
    graph.add_node("revise_plan", revise_plan)
    graph.add_node("human_review", human_review)
    graph.add_node("meal_plan_review", meal_plan_review)
    graph.add_node("handle_cancel", handle_cancel)
    graph.add_node("handle_meal_plan_approval", handle_meal_plan_approval)
    graph.add_node("agent3_build_grocery_list", agent3_build_grocery_list)
    graph.add_node("agent3_price_groceries", agent3_price_groceries)
    graph.add_node("agent3_check_budget", agent3_check_budget)
    graph.add_node("budget_failure", budget_failure)
    graph.add_node("pricing_unknown", pricing_unknown)
    graph.add_node("shopping_review", shopping_review)
    graph.add_node("prepare_cost_revision", prepare_cost_revision)
    graph.add_node("finalize_plan", finalize_plan)

    # STEP 3 — Build the plan and explicitly check completeness.
    graph.add_edge(START, "agent1_retrieve")
    graph.add_edge("agent1_retrieve", "agent1_build_plan")
    graph.add_conditional_edges(
        "agent1_build_plan",
        route_after_plan_build,
        {
            "planning_failure": "planning_failure",
            "validate": "agent2_validate",
        },
    )

    graph.add_conditional_edges(
        "planning_failure",
        route_after_planning_failure,
        {
            "modify_settings": "wait_for_settings_change",
            "cancel": "handle_cancel",
        },
    )

    # STEP 4-5 — Agent 2 validation and automatic revision.
    graph.add_conditional_edges(
        "agent2_validate",
        route_after_validation,
        {
            "revise": "revise_plan",
            "human_review": "human_review",
            "meal_plan_review": "meal_plan_review",
        },
    )

    graph.add_edge("revise_plan", "agent1_build_plan")

    # STEP 6 — Human meal review and explicit replacement outcomes.
    graph.add_conditional_edges(
        "meal_plan_review",
        route_after_meal_plan_review,
        {
            "replace": "agent1_replace_meal",
            "cancel": "handle_cancel",
            "approve": "handle_meal_plan_approval",
        },
    )

    graph.add_conditional_edges(
        "agent1_replace_meal",
        route_after_replacement,
        {
            "replacement_failure": "replacement_failure",
            "validate": "agent2_validate",
        },
    )

    graph.add_conditional_edges(
        "replacement_failure",
        route_after_replacement_failure,
        {
            "meal_plan_review": "meal_plan_review",
            "modify_settings": "wait_for_settings_change",
            "cancel": "handle_cancel",
        },
    )

    # STEP 7-10 — Shopping and cost-driven replacement.
    graph.add_edge(
        "handle_meal_plan_approval",
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
        route_after_budget_result,
        {
            "shopping_review": "shopping_review",
            "budget_failure": "budget_failure",
            "pricing_unknown": "pricing_unknown",
        },
    )

    graph.add_conditional_edges(
        "budget_failure",
        route_after_budget_failure,
        {
            "replace_for_cost": "prepare_cost_revision",
            "modify_settings": "wait_for_settings_change",
            "cancel": "handle_cancel",
        },
    )

    graph.add_conditional_edges(
        "pricing_unknown",
        route_after_pricing_unknown,
        {
            "shopping_review": "shopping_review",
            "modify_settings": "wait_for_settings_change",
            "cancel": "handle_cancel",
        },
    )

    graph.add_conditional_edges(
        "shopping_review",
        route_after_shopping_review,
        {
            "replace_for_cost": "prepare_cost_revision",
            "cancel": "handle_cancel",
            "finalize": "finalize_plan",
        },
    )

    graph.add_edge(
        "prepare_cost_revision",
        "agent1_replace_meal",
    )

    graph.add_edge("wait_for_settings_change", END)
    graph.add_edge("human_review", END)
    graph.add_edge("handle_cancel", END)
    graph.add_edge("finalize_plan", END)

    connection = sqlite3.connect(
        "data/meal_plan_checkpoints.db",
        check_same_thread=False,
    )

    return graph.compile(
        checkpointer=SqliteSaver(connection)
    )


meal_plan_graph = build_graph()
