import csv
import json
from pathlib import Path

from src.agents.nutrition_safety import validate_recipe_with_agent2


DATA_DIR = Path("data")
RECIPES_FILE = DATA_DIR / "challenge_recipes.json"
GOLDEN_FILE = DATA_DIR / "validation_golden.csv"


def load_recipes():
    """Load challenge recipes and index them by recipe ID."""
    with open(RECIPES_FILE) as file:
        recipes = json.load(file)

    return {
        recipe["recipe_id"]: recipe
        for recipe in recipes
    }


def load_golden_cases():
    """Load the expected Agent 2 validation results."""
    with open(GOLDEN_FILE, newline="") as file:
        return list(
            csv.DictReader(file)
        )


def build_requirements(case):
    """Convert one golden test case into validator requirements."""
    constraint_type = case["constraint_type"]
    constraint = case["constraint"]

    requirements = {
        "diet": None,
        "meal_type": None,
        "min_protein": None,
        "excluded_ingredients": [],
    }

    if constraint_type == "diet":
        requirements["diet"] = constraint

    elif constraint_type == "meal_type":
        requirements["meal_type"] = constraint

    elif constraint_type == "min_protein":
        requirements["min_protein"] = float(
            constraint
        )

    elif constraint_type == "exclude_ingredient":
        requirements["excluded_ingredients"] = [
            constraint
        ]

    return requirements


def evaluate():
    """Compare deterministic Agent 2 validation with the golden dataset."""
    recipes = load_recipes()
    golden_cases = load_golden_cases()

    correct_count = 0

    print()
    print("Agent 2 enhanced validation baseline")
    print("-" * 70)

    for case in golden_cases:
        recipe = recipes[
            case["recipe_id"]
        ]

        requirements = build_requirements(
            case
        )

        result = validate_recipe_with_agent2(
            recipe,
            requirements,
        )

        predicted_status = result["status"]
        expected_status = case["expected_status"]

        is_correct = (
            predicted_status == expected_status
        )

        if is_correct:
            correct_count += 1

        result_marker = (
            "PASS"
            if is_correct
            else "MISS"
        )

        print(
            f"{case['case_id']} | "
            f"{recipe['recipe_name']} | "
            f"expected={expected_status} | "
            f"predicted={predicted_status} | "
            f"{result_marker}"
        )

    total_cases = len(golden_cases)

    accuracy = (
        correct_count / total_cases
        if total_cases
        else 0
    )

    print("-" * 70)
    print(
        f"Correct: {correct_count}/{total_cases}"
    )
    print(
        f"Accuracy: {accuracy:.1%}"
    )

    return accuracy


if __name__ == "__main__":
    evaluate()
