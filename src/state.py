from typing import TypedDict

class MealPlanState(TypedDict, total=False):
    """Shared state; sections map directly to the high-level agent flow."""

    # STEP 1-2 — Requirements and missing-information HITL.
    user_request: str
    days: int
    meal_slots: list[str]
    diet: str
    excluded_ingredients: list[str]
    allergens: list[str]
    min_protein_per_meal: float | None
    budget: float | None
    missing_requirements: list[str]

    # STEP 3 — Agent 1 recipe retrieval and draft planning.
    candidate_recipes: list[dict]
    draft_meal_plan: list[dict]
    planning_attempts: int

    # STEP 4-5 — Agent 2 validation and revision.
    validation_status: str | None
    validation_violations: list[dict]
    meals_to_replace: list[str]

    # STEP 6 — Human meal-plan approval.
    meal_plan_approval: str | None
    meal_plan_feedback: str | None

    # STEP 7-9 — Agent 3 grocery list, pricing, and budget.
    grocery_list: list[dict]
    priced_grocery_list: list[dict]
    estimated_total: float | None
    budget_status: str | None
    pricing_errors: list[str]

    # STEP 10-11 — Final approval and response.
    final_approval: str | None
    final_feedback: str | None
    final_response: str | None
