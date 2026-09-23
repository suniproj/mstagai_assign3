from collections import Counter

from src.mcp_clients.recipe_client import search_recipe_tool


MEAL_TYPE_MAP = {
    "breakfast": "breakfast",
    "lunch": "lunch/dinner",
    "dinner": "lunch/dinner",
    "snack": "snack",
}


def get_recipe_requirements(state):
    """STEP 3 — Calculate recipe needs for each dataset meal category."""
    days = state.get("days", 1)
    meal_slots = state.get("meal_slots", ["breakfast", "lunch", "dinner"])
    required_counts = Counter()

    for meal_slot in meal_slots:
        required_counts[MEAL_TYPE_MAP[meal_slot]] += days

    return required_counts


def retrieve_candidates(state):
    """STEP 3 — Agent 1 retrieves candidates for the requested constraints."""
    candidates = []

    for meal_type, needed in get_recipe_requirements(state).items():
        recipes = search_recipe_tool(
            query=f"{state.get('diet') or ''} {meal_type} meal".strip(),
            diet=state.get("diet"),
            meal_type=meal_type,
            min_protein=state.get("min_protein_per_meal"),
            top_k=max(needed + 4, 5),
        )

        for recipe in recipes:
            recipe["dataset_meal_type"] = meal_type

        candidates.extend(recipes)

    return {
        "candidate_recipes": candidates,
        "planning_attempts": state.get("planning_attempts", 0) + 1,
    }


def build_draft_meal_plan(state):
    """
    STEP 3 — Build one primary recipe per requested meal slot.

    A complete plan must contain every requested day/meal slot. Missing slots
    are returned explicitly instead of allowing an incomplete plan to appear
    successful.
    """
    days = state.get("days", 1)
    meal_slots = state.get("meal_slots", ["breakfast", "lunch", "dinner"])
    candidates = state.get("candidate_recipes", [])

    plan = []
    usage_count = Counter()

    for day_number in range(1, days + 1):
        used_today = set()

        for meal_slot in meal_slots:
            meal_type = MEAL_TYPE_MAP[meal_slot]

            available = [
                recipe
                for recipe in candidates
                if recipe.get("dataset_meal_type") == meal_type
                and recipe.get("recipe_id") not in used_today
            ]

            if not available:
                continue

            available.sort(
                key=lambda recipe: usage_count[recipe["recipe_id"]]
            )

            selected = available[0]
            used_today.add(selected["recipe_id"])
            usage_count[selected["recipe_id"]] += 1

            plan.append({
                "day": day_number,
                "meal_slot": meal_slot,
                "dataset_meal_type": meal_type,
                "recipe": selected,
            })

    planned_slots = {
        (meal["day"], meal["meal_slot"])
        for meal in plan
    }

    missing_slots = [
        {
            "day": day_number,
            "meal_slot": meal_slot,
        }
        for day_number in range(1, days + 1)
        for meal_slot in meal_slots
        if (day_number, meal_slot) not in planned_slots
    ]

    expected_count = days * len(meal_slots)
    actual_count = len(plan)

    if missing_slots:
        protein = state.get("min_protein_per_meal")

        constraint_hint = (
            f" Minimum protein is {protein:g}g per meal."
            if protein is not None
            else ""
        )

        message = (
            f"Could not create the complete requested meal plan. "
            f"Required {expected_count} meal slots but found suitable recipes "
            f"for {actual_count}.{constraint_hint} "
            "Please modify one or more requirements and try again."
        )

        plan_status = "INCOMPLETE"
    else:
        message = None
        plan_status = "COMPLETE"

    return {
        "draft_meal_plan": plan,
        "plan_status": plan_status,
        "planning_message": message,
        "missing_meal_slots": missing_slots,
    }


def replace_requested_meal(state):
    """
    STEP 6/10 — Replace one meal for preference or cost.

    If no alternative can satisfy the request, return an explicit replacement
    failure instead of silently continuing.
    """
    request = state.get("revision_request") or {}
    day_number = request.get("day")
    meal_slot = request.get("meal_slot")
    feedback = (request.get("feedback") or "").strip()

    if day_number is None or not meal_slot:
        return {
            "plan_status": "INCOMPLETE",
            "planning_message": (
                "The replacement request did not identify a valid meal slot."
            ),
        }

    plan = list(state.get("draft_meal_plan", []))
    rejected_ids = set(state.get("rejected_recipe_ids", []))

    rejected_id = request.get("rejected_recipe_id")

    if rejected_id:
        rejected_ids.add(rejected_id)

    meal_type = MEAL_TYPE_MAP[meal_slot]

    query = " ".join(
        part
        for part in [
            feedback,
            state.get("diet") or "",
            meal_slot,
            "meal",
        ]
        if part
    )

    alternatives = search_recipe_tool(
        query=query,
        diet=state.get("diet"),
        meal_type=meal_type,
        min_protein=state.get("min_protein_per_meal"),
        top_k=10,
    )

    used_same_day = {
        meal["recipe"]["recipe_id"]
        for meal in plan
        if meal["day"] == day_number
        and meal["meal_slot"] != meal_slot
    }

    replacement = next(
        (
            recipe
            for recipe in alternatives
            if recipe.get("recipe_id") not in rejected_ids
            and recipe.get("recipe_id") not in used_same_day
        ),
        None,
    )

    if replacement is None:
        return {
            "rejected_recipe_ids": list(rejected_ids),
            "plan_status": "REPLACEMENT_FAILED",
            "planning_message": (
                f"Could not find another suitable recipe for Day {day_number} "
                f"{meal_slot}. Try changing the replacement preference or "
                "modify the plan settings."
            ),
        }

    replacement["dataset_meal_type"] = meal_type

    updated_plan = []

    for meal in plan:
        if (
            meal["day"] == day_number
            and meal["meal_slot"] == meal_slot
        ):
            updated_plan.append({
                "day": day_number,
                "meal_slot": meal_slot,
                "dataset_meal_type": meal_type,
                "recipe": replacement,
            })
        else:
            updated_plan.append(meal)

    return {
        "draft_meal_plan": updated_plan,
        "rejected_recipe_ids": list(rejected_ids),
        "planning_attempts": state.get("planning_attempts", 0) + 1,
        "plan_status": "COMPLETE",
        "planning_message": None,
        "missing_meal_slots": [],
        "revision_request": None,
        "meal_plan_approval": None,
        "shopping_review_action": None,
    }
