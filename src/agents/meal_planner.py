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
    meal_slots = state.get(
        "meal_slots",
        ["breakfast", "lunch", "dinner"],
    )

    required_counts = Counter()

    for meal_slot in meal_slots:
        dataset_meal_type = MEAL_TYPE_MAP[
            meal_slot
        ]

        required_counts[
            dataset_meal_type
        ] += days

    return required_counts


def retrieve_candidates(state):
    """STEP 3 — Agent 1 retrieves enough candidates for the requested plan."""
    diet = state.get("diet")
    min_protein = state.get(
        "min_protein_per_meal"
    )

    required_counts = get_recipe_requirements(
        state
    )

    candidate_recipes = []

    for dataset_meal_type, required_count in required_counts.items():

        # Retrieve spare candidates for variety and Agent 2 revisions.
        top_k = max(
            required_count + 4,
            5,
        )

        query = (
            f"{diet or ''} "
            f"{dataset_meal_type} meal"
        ).strip()

        recipes = search_recipe_tool(
            query=query,
            diet=diet,
            meal_type=dataset_meal_type,
            min_protein=min_protein,
            top_k=top_k,
        )

        for recipe in recipes:
            recipe["dataset_meal_type"] = (
                dataset_meal_type
            )

        candidate_recipes.extend(
            recipes
        )

    return {
        "candidate_recipes": candidate_recipes,
        "planning_attempts": (
            state.get("planning_attempts", 0)
            + 1
        ),
    }


def build_draft_meal_plan(state):
    """
    STEP 3 — Agent 1 assigns recipes to each day and meal slot.

    A recipe cannot repeat on the same day. Recipes not used on previous
    days are preferred, but previous-day recipes may be reused when needed.
    """
    days = state.get("days", 1)

    meal_slots = state.get(
        "meal_slots",
        ["breakfast", "lunch", "dinner"],
    )

    candidate_recipes = state.get(
        "candidate_recipes",
        []
    )

    draft_meal_plan = []

    recipe_usage_count = Counter()

    for day_number in range(1, days + 1):

        # Hard rule: the same recipe cannot appear twice on one day.
        recipes_used_today = set()

        for meal_slot in meal_slots:

            dataset_meal_type = MEAL_TYPE_MAP[
                meal_slot
            ]

            available_recipes = [
                recipe
                for recipe in candidate_recipes
                if (
                    recipe.get(
                        "dataset_meal_type"
                    )
                    == dataset_meal_type
                    and recipe.get(
                        "recipe_id"
                    )
                    not in recipes_used_today
                )
            ]

            if not available_recipes:
                continue

            # Prefer recipes used least often on previous days.
            available_recipes.sort(
                key=lambda recipe:
                    recipe_usage_count[
                        recipe["recipe_id"]
                    ]
            )

            selected_recipe = (
                available_recipes[0]
            )

            recipe_id = selected_recipe[
                "recipe_id"
            ]

            recipes_used_today.add(
                recipe_id
            )

            recipe_usage_count[
                recipe_id
            ] += 1

            draft_meal_plan.append({
                "day": day_number,
                "meal_slot": meal_slot,
                "dataset_meal_type": (
                    dataset_meal_type
                ),
                "recipe": selected_recipe,
            })

    return {
        "draft_meal_plan": draft_meal_plan
    }

