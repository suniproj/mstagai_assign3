from src.recipe_repository import build_metadata_filter

def test_build_metadata_filter():
    assert build_metadata_filter("Vegan", "lunch/dinner", 15) == {
        "health_labels": {"$in": ["Vegan"]},
        "meal_type": {"$in": ["lunch/dinner"]},
        "protein_per_serving": {"$gte": 15},
    }

def test_empty_metadata_filter():
    assert build_metadata_filter() is None
