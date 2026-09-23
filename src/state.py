from typing import TypedDict


class MealPlanState(TypedDict, total=False):
    """Shared state passed between agents and LangGraph nodes."""

    # STEP 1-2 — User requirements.
    user_request: str
    days: int
    meal_slots: list[str]
    diet: str
    excluded_ingredients: list[str]
    allergens: list[str]
    min_protein_per_meal: float | None
    budget: float | None

    # STEP 3 — Agent 1 planning and explicit planning outcome.
    candidate_recipes: list[dict]
    draft_meal_plan: list[dict]
    planning_attempts: int
    plan_status: str | None
    planning_message: str | None
    missing_meal_slots: list[dict]
    revision_request: dict | None
    rejected_recipe_ids: list[str]

    # STEP 4-6 — Agent 2 and meal-plan HITL.
    validation_status: str | None
    validation_violations: list[dict]
    meals_to_replace: list[dict]
    meal_plan_approval: str | None
    meal_plan_feedback: str | None

    # STEP 7-11 — Agent 3 and shopping HITL.
    grocery_list: list[dict]
    priced_grocery_list: list[dict]
    estimated_total: float | None
    budget_status: str | None
    pricing_errors: list[str]
    shopping_review_action: str | None
    final_approval: str | None
    final_response: str | None
