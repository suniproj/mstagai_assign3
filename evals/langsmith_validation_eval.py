import json
from pathlib import Path

from dotenv import load_dotenv
from langsmith import Client

from src.agents.nutrition_safety import (
    validate_recipe_with_agent2,
)


load_dotenv()

DATA_FILE = Path(
    "data/challenge_recipes.json"
)

DATASET_NAME = (
    "agent2-nutrition-safety-eval"
)


def load_recipes():
    """Load challenge recipes by recipe ID."""
    with open(DATA_FILE) as file:
        recipes = json.load(file)

    return {
        recipe["recipe_id"]: recipe
        for recipe in recipes
    }


def build_eval_cases():
    """
    Representative Agent 2 cases:

    semantic soy conflict,
    semantic mushroom conflict,
    explicit safe case,
    protein failure,
    ambiguous evidence.
    """
    return [
        {
            "recipe_id": "challenge-001",
            "requirements": {
                "diet": None,
                "meal_type": None,
                "min_protein": None,
                "excluded_ingredients": [
                    "soy"
                ],
            },
            "expected_status": "FAIL",
        },
        {
            "recipe_id": "challenge-002",
            "requirements": {
                "diet": None,
                "meal_type": None,
                "min_protein": None,
                "excluded_ingredients": [
                    "mushroom"
                ],
            },
            "expected_status": "FAIL",
        },
        {
            "recipe_id": "challenge-006",
            "requirements": {
                "diet": None,
                "meal_type": None,
                "min_protein": None,
                "excluded_ingredients": [
                    "soy"
                ],
            },
            "expected_status": "PASS",
        },
        {
            "recipe_id": "challenge-010",
            "requirements": {
                "diet": None,
                "meal_type": None,
                "min_protein": 15,
                "excluded_ingredients": [],
            },
            "expected_status": "FAIL",
        },
        {
            "recipe_id": "challenge-014",
            "requirements": {
                "diet": None,
                "meal_type": None,
                "min_protein": None,
                "excluded_ingredients": [
                    "dairy"
                ],
            },
            "expected_status": (
                "NEEDS_REVIEW"
            ),
        },
    ]


def target(inputs):
    """Run Agent 2 for one LangSmith evaluation example."""
    recipes = load_recipes()

    recipe = recipes[
        inputs["recipe_id"]
    ]

    result = (
        validate_recipe_with_agent2(
            recipe,
            inputs["requirements"],
        )
    )

    return {
        "status": result["status"]
    }


def status_match(
    outputs,
    reference_outputs,
):
    """Score 1 when Agent 2 returns the golden status."""
    return {
        "key": "status_match",
        "score": int(
            outputs["status"]
            == reference_outputs[
                "expected_status"
            ]
        ),
    }


def main():
    client = Client()

    # Create the dataset only if it does not already exist.
    existing_datasets = list(
        client.list_datasets(
            dataset_name=DATASET_NAME
        )
    )

    if existing_datasets:
        dataset = existing_datasets[0]

    else:
        dataset = client.create_dataset(
            dataset_name=DATASET_NAME,
            description=(
                "Representative golden cases "
                "for Agent 2 nutrition and "
                "safety validation."
            ),
        )

        recipes = load_recipes()

        for case in build_eval_cases():
            client.create_example(
                dataset_id=dataset.id,
                inputs={
                    "recipe_id":
                        case["recipe_id"],
                    "requirements":
                        case[
                            "requirements"
                        ],
                },
                outputs={
                    "expected_status":
                        case[
                            "expected_status"
                        ],
                },
            )

    results = client.evaluate(
        target,
        data=DATASET_NAME,
        evaluators=[
            status_match
        ],
        experiment_prefix=(
            "agent2-validation"
        ),
    )

    print(results)


if __name__ == "__main__":
    main()

