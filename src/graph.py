import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from src.agents.meal_planner import build_draft_meal_plan, replace_requested_meal, retrieve_candidates
from src.agents.nutrition_safety import validate_meal_plan
from src.agents.shopping_budget import create_grocery_list, evaluate_budget, price_grocery_list
from src.state import MealPlanState

MAX_PLANNING_ATTEMPTS = 3

def agent1_retrieve(state):
    # STEP 3 — Agent 1 retrieves.
    return retrieve_candidates(state)

def agent1_build_plan(state):
    # STEP 3 — Agent 1 plans.
    return build_draft_meal_plan(state)

def agent1_replace_meal(state):
    # STEP 6/10 — Agent 1 replaces one selected meal.
    return replace_requested_meal(state)

def agent2_validate(state):
    # STEP 4 — Agent 2 validates.
    return validate_meal_plan(state)

def route_after_validation(state):
    status = state.get("validation_status")
    if status == "FAIL":
        if state.get("planning_attempts", 0) >= MAX_PLANNING_ATTEMPTS:
            return "human_review"
        return "revise"
    if status == "NEEDS_REVIEW":
        return "human_review"
    return "meal_plan_review"

def revise_plan(state):
    # STEP 5 — Remove recipes rejected by Agent 2.
    failed_ids = {meal["recipe_id"] for meal in state.get("meals_to_replace", [])}
    return {
        "candidate_recipes": [
            recipe for recipe in state.get("candidate_recipes", [])
            if recipe.get("recipe_id") not in failed_ids
        ]
    }

def human_review(state):
    return {"final_response": "Human review is required before continuing."}

def meal_plan_review(state):
    # STEP 6 — Recipe-level human review.
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
        return "decline"
    return "approve"

def handle_decline(state):
    return {"final_response": "Plan declined by user."}

def handle_meal_plan_approval(state):
    return {}

def agent3_build_grocery_list(state):
    # STEP 7 — Agent 3 builds groceries.
    return create_grocery_list(state)

def agent3_price_groceries(state):
    # STEP 8 — Agent 3 uses Price MCP capability.
    return price_grocery_list(state)

def agent3_check_budget(state):
    # STEP 9 — Agent 3 checks budget.
    return evaluate_budget(state)

def shopping_review(state):
    # STEP 10 — Human can approve or request a cheaper meal.
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
        return "decline"
    return "finalize"

def prepare_cost_revision(state):
    request = dict(state.get("revision_request") or {})
    request["reason"] = "cost"
    if not request.get("feedback"):
        request["feedback"] = "cheaper alternative"
    return {"revision_request": request}

def finalize_plan(state):
    # STEP 11 — Final approved output.
    return {
        "final_approval": "approve",
        "final_response": "Meal plan and shopping plan approved.",
    }

def build_graph():
    graph = StateGraph(MealPlanState)
    graph.add_node("agent1_retrieve", agent1_retrieve)
    graph.add_node("agent1_build_plan", agent1_build_plan)
    graph.add_node("agent1_replace_meal", agent1_replace_meal)
    graph.add_node("agent2_validate", agent2_validate)
    graph.add_node("revise_plan", revise_plan)
    graph.add_node("human_review", human_review)
    graph.add_node("meal_plan_review", meal_plan_review)
    graph.add_node("handle_decline", handle_decline)
    graph.add_node("handle_meal_plan_approval", handle_meal_plan_approval)
    graph.add_node("agent3_build_grocery_list", agent3_build_grocery_list)
    graph.add_node("agent3_price_groceries", agent3_price_groceries)
    graph.add_node("agent3_check_budget", agent3_check_budget)
    graph.add_node("shopping_review", shopping_review)
    graph.add_node("prepare_cost_revision", prepare_cost_revision)
    graph.add_node("finalize_plan", finalize_plan)

    graph.add_edge(START, "agent1_retrieve")
    graph.add_edge("agent1_retrieve", "agent1_build_plan")
    graph.add_edge("agent1_build_plan", "agent2_validate")
    graph.add_conditional_edges("agent2_validate", route_after_validation, {
        "revise": "revise_plan",
        "human_review": "human_review",
        "meal_plan_review": "meal_plan_review",
    })
    graph.add_edge("revise_plan", "agent1_build_plan")
    graph.add_conditional_edges("meal_plan_review", route_after_meal_plan_review, {
        "replace": "agent1_replace_meal",
        "decline": "handle_decline",
        "approve": "handle_meal_plan_approval",
    })
    graph.add_edge("agent1_replace_meal", "agent2_validate")
    graph.add_edge("handle_meal_plan_approval", "agent3_build_grocery_list")
    graph.add_edge("agent3_build_grocery_list", "agent3_price_groceries")
    graph.add_edge("agent3_price_groceries", "agent3_check_budget")
    graph.add_edge("agent3_check_budget", "shopping_review")
    graph.add_conditional_edges("shopping_review", route_after_shopping_review, {
        "replace_for_cost": "prepare_cost_revision",
        "decline": "handle_decline",
        "finalize": "finalize_plan",
    })
    graph.add_edge("prepare_cost_revision", "agent1_replace_meal")
    graph.add_edge("human_review", END)
    graph.add_edge("handle_decline", END)
    graph.add_edge("finalize_plan", END)

    connection = sqlite3.connect(
        "data/meal_plan_checkpoints.db",
        check_same_thread=False,
    )
    return graph.compile(checkpointer=SqliteSaver(connection))

meal_plan_graph = build_graph()
