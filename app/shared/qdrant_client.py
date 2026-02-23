"""
Qdrant client singleton for vector storage and indexing.

Uses QDRANT_URL and QDRANT_API_KEY from config.
"""
import logging
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from app.core.config import settings

logger = logging.getLogger(__name__)

_qdrant_client: Optional[QdrantClient] = None


def get_qdrant_client() -> QdrantClient:
    """Get or create the Qdrant client singleton."""
    global _qdrant_client
    if _qdrant_client is None:
        kwargs = {"url": settings.qdrant_url}
        if getattr(settings, "qdrant_api_key", None):
            kwargs["api_key"] = settings.qdrant_api_key
        _qdrant_client = QdrantClient(**kwargs)
        logger.info("Qdrant client initialized: %s", settings.qdrant_url)
    return _qdrant_client


def ensure_collection(
    collection_name: str,
    vector_size: int,
    distance: Distance = Distance.COSINE,
) -> None:
    """
    Create the collection if it does not exist.

    Args:
        collection_name: Name of the Qdrant collection.
        vector_size: Dimension of the vectors (e.g. 768 for gemini-embedding-001).
        distance: Distance metric (COSINE, EUCLID, DOT).
    """
    client = get_qdrant_client()
    try:
        client.get_collection(collection_name)
        logger.debug("Collection already exists: %s", collection_name)
    except Exception:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=distance),
        )
        logger.info("Created Qdrant collection: %s (size=%s)", collection_name, vector_size)


def upsert_points(
    collection_name: str,
    points: list[PointStruct],
) -> None:
    """Upsert points into a collection."""
    client = get_qdrant_client()
    client.upsert(collection_name=collection_name, points=points)


def delete_points_by_ids(collection_name: str, ids: list[str]) -> None:
    """Delete points by their IDs (external IDs)."""
    client = get_qdrant_client()
    client.delete(collection_name=collection_name, points_selector=ids)
