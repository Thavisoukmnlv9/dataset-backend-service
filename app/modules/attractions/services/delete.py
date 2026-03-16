"""Delete attraction from PostgreSQL."""
import logging
from typing import Dict

from fastapi import HTTPException, status

from app.prisma import prisma
from app.shared.utils.responses.response import create_success_response

logger = logging.getLogger(__name__)


async def delete_attraction(attraction_id: str) -> Dict:
    """Hard delete attraction."""
    try:
        existing = await prisma.attraction.find_unique(where={"id": attraction_id})
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attraction not found")
        await prisma.attraction.delete(where={"id": attraction_id})
        return create_success_response(message="Attraction deleted successfully", data={"id": attraction_id})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("delete_attraction error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
