from pinecone import Pinecone
from .config import settings

def get_recipe_index():
    """Connect to the existing Assignment 2 Pinecone recipe index."""
    if not settings.pinecone_api_key:
        raise RuntimeError("PINECONE_API_KEY is not set in .env")
    pinecone = Pinecone(api_key=settings.pinecone_api_key)
    return pinecone.Index(settings.pinecone_index)
