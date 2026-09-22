from .config import settings
from .embeddings import get_embeddings
from .pinecone_store import get_recipe_index

def build_metadata_filter(diet=None, meal_type=None, min_protein=None):
    """Build exact constraints from Agent 1's structured requirements."""
    conditions = {}
    if diet:
        conditions["health_labels"] = {"$in": [diet]}
    if meal_type:
        conditions["meal_type"] = {"$in": [meal_type]}
    if min_protein is not None:
        conditions["protein_per_serving"] = {"$gte": min_protein}
    return conditions or None

def search_recipes(query, diet=None, meal_type=None, min_protein=None, top_k=None):
    """Search Pinecone and return structured recipe evidence to Agent 1."""
    number_of_results = top_k if top_k is not None else settings.top_k
    embedding_model = get_embeddings()
    recipe_index = get_recipe_index()

    # STEP 3 — Semantic retrieval plus exact metadata constraints.
    query_vector = embedding_model.embed_query(query)
    metadata_filter = build_metadata_filter(diet, meal_type, min_protein)

    search_arguments = {
        "vector": query_vector,
        "top_k": number_of_results,
        "include_metadata": True,
    }
    if metadata_filter:
        search_arguments["filter"] = metadata_filter

    search_results = recipe_index.query(**search_arguments)
    recipes = []

    # Return records, not a generated RAG answer; the agents decide what happens next.
    for match in search_results.matches:
        metadata = dict(match.metadata or {})
        recipes.append({
            "recipe_id": match.id,
            "recipe_name": metadata.get("recipe_name", ""),
            "meal_type": metadata.get("meal_type", []),
            "diet_labels": metadata.get("diet_labels", []),
            "health_labels": metadata.get("health_labels", []),
            "servings": metadata.get("servings"),
            "calories_per_serving": metadata.get("calories_per_serving"),
            "protein_per_serving": metadata.get("protein_per_serving"),
            "source": metadata.get("source", ""),
            "url": metadata.get("url", ""),
            "recipe_text": metadata.get("text", ""),
            "similarity_score": float(match.score),
        })
    return recipes
