"""Delete restaurant from PostgreSQL and Qdrant."""
import logging
from typing import Dict

from fastapi import HTTPException, status

from app.prisma import prisma

logger = logging.getLogger(__name__)

QDRANT_COLLECTION = "restaurants"


async def delete_restaurant(restaurant_id: str) -> Dict:
    """Soft delete not used (no deleted_at on Restaurant); hard delete and remove from Qdrant."""
    from app.shared.qdrant_client import get_qdrant_client
    from app.shared.utils.responses.response import create_success_response

    try:
        existing = await prisma.restaurant.find_unique(where={"id": restaurant_id})
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")
        await prisma.restaurant.delete(where={"id": restaurant_id})
        try:
            client = get_qdrant_client()
            client.delete(collection_name=QDRANT_COLLECTION, points_selector=[restaurant_id, f"{restaurant_id}_cover"])
        except Exception as e:
            logger.warning("Qdrant delete failed: %s", e)
        return create_success_response(message="Restaurant deleted successfully", data={"id": restaurant_id})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("delete_restaurant error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
