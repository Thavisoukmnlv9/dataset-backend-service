"""Delete cafe from PostgreSQL (no Qdrant)."""
import logging
from typing import Dict

from fastapi import HTTPException, status

from app.prisma import prisma
from app.shared.utils.responses.response import create_success_response

logger = logging.getLogger(__name__)


async def delete_cafe(cafe_id: str) -> Dict:
    """Hard delete cafe and related records (cascade via Prisma)."""
    try:
        existing = await prisma.cafe.find_unique(where={"id": cafe_id})
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cafe not found")
        await prisma.cafe.delete(where={"id": cafe_id})
        return create_success_response(message="Cafe deleted successfully", data={"id": cafe_id})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("delete_cafe error: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
