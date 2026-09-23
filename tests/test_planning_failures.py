from src.agents.meal_planner import build_draft_meal_plan


def test_incomplete_plan_reports_missing_slots():
    """An unsatisfied request must return an explicit incomplete outcome."""
    state = {
        "days": 1,
        "meal_slots": [
            "breakfast",
            "lunch",
            "dinner",
        ],
        "min_protein_per_meal": 100,
        "candidate_recipes": [],
    }

    result = build_draft_meal_plan(state)

    assert result["plan_status"] == "INCOMPLETE"
    assert len(result["missing_meal_slots"]) == 3
    assert "Could not create" in result["planning_message"]


def test_complete_plan_reports_complete():
    """A plan containing every requested slot is marked complete."""
    state = {
        "days": 1,
        "meal_slots": ["breakfast"],
        "candidate_recipes": [
            {
                "recipe_id": "recipe-test",
                "recipe_name": "Test Breakfast",
                "dataset_meal_type": "breakfast",
            }
        ],
    }

    result = build_draft_meal_plan(state)

    assert result["plan_status"] == "COMPLETE"
    assert result["missing_meal_slots"] == []
    assert result["planning_message"] is None
