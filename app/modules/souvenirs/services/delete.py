"""Delete souvenir from PostgreSQL (no Qdrant)."""
import logging
from typing import Dict

from fastapi import HTTPException, status

from app.prisma import prisma
from app.shared.utils.responses.response import create_success_response

logger = logging.getLogger(__name__)


async def delete_souvenir(souvenir_id: str) -> Dict:
    """Hard delete souvenir and related records (cascade via Prisma)."""
    try:
        existing = await prisma.souvenir.find_unique(where={"id": souvenir_id})
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Souvenir not found")
        await prisma.souvenir.delete(where={"id": souvenir_id})
        return create_success_response(message="Souvenir deleted successfully", data={"id": souvenir_id})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("delete_souvenir error: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
