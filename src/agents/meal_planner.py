from collections import Counter
from src.mcp_clients.recipe_client import search_recipe_tool

MEAL_TYPE_MAP = {
    "breakfast": "breakfast",
    "lunch": "lunch/dinner",
    "dinner": "lunch/dinner",
    "snack": "snack",
}

def get_recipe_requirements(state):
    # STEP 3 — Count recipes needed from each dataset category.
    counts = Counter()
    for slot in state.get("meal_slots", ["breakfast", "lunch", "dinner"]):
        counts[MEAL_TYPE_MAP[slot]] += state.get("days", 1)
    return counts

def retrieve_candidates(state):
    # STEP 3 — Retrieve candidates for the initial plan.
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
    # STEP 3 — One primary recipe per slot; no same-day duplicate.
    plan = []
    usage = Counter()
    candidates = state.get("candidate_recipes", [])
    for day in range(1, state.get("days", 1) + 1):
        used_today = set()
        for slot in state.get("meal_slots", ["breakfast", "lunch", "dinner"]):
            meal_type = MEAL_TYPE_MAP[slot]
            available = [
                recipe for recipe in candidates
                if recipe.get("dataset_meal_type") == meal_type
                and recipe.get("recipe_id") not in used_today
            ]
            if not available:
                continue
            available.sort(key=lambda recipe: usage[recipe["recipe_id"]])
            selected = available[0]
            used_today.add(selected["recipe_id"])
            usage[selected["recipe_id"]] += 1
            plan.append({
                "day": day,
                "meal_slot": slot,
                "dataset_meal_type": meal_type,
                "recipe": selected,
            })
    return {"draft_meal_plan": plan}

def replace_requested_meal(state):
    # STEP 6/10 — Replace one meal for preference or cost.
    request = state.get("revision_request") or {}
    day = request.get("day")
    slot = request.get("meal_slot")
    feedback = (request.get("feedback") or "").strip()
    if day is None or not slot:
        return {}

    plan = list(state.get("draft_meal_plan", []))
    rejected_ids = set(state.get("rejected_recipe_ids", []))
    rejected_id = request.get("rejected_recipe_id")
    if rejected_id:
        rejected_ids.add(rejected_id)

    meal_type = MEAL_TYPE_MAP[slot]
    query = " ".join(
        part for part in [feedback, state.get("diet") or "", slot, "meal"]
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
        if meal["day"] == day and meal["meal_slot"] != slot
    }
    replacement = next(
        (
            recipe for recipe in alternatives
            if recipe.get("recipe_id") not in rejected_ids
            and recipe.get("recipe_id") not in used_same_day
        ),
        None,
    )
    if replacement is None:
        return {
            "rejected_recipe_ids": list(rejected_ids),
            "validation_status": "NEEDS_REVIEW",
        }

    replacement["dataset_meal_type"] = meal_type
    updated = []
    for meal in plan:
        if meal["day"] == day and meal["meal_slot"] == slot:
            updated.append({
                "day": day,
                "meal_slot": slot,
                "dataset_meal_type": meal_type,
                "recipe": replacement,
            })
        else:
            updated.append(meal)

    return {
        "draft_meal_plan": updated,
        "rejected_recipe_ids": list(rejected_ids),
        "planning_attempts": state.get("planning_attempts", 0) + 1,
        "revision_request": None,
        "meal_plan_approval": None,
        "shopping_review_action": None,
    }
