from langchain_huggingface import HuggingFaceEmbeddings
from .config import settings

_embedding_model = None

def get_embeddings():
    """Return the same local embedding model used by Assignment 2."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = HuggingFaceEmbeddings(model_name=settings.embedding_model)
    return _embedding_model
