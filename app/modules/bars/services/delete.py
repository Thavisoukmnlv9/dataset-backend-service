"""Delete bar from PostgreSQL (no Qdrant)."""
import logging
from typing import Dict

from fastapi import HTTPException, status

from app.prisma import prisma
from app.shared.utils.responses.response import create_success_response

logger = logging.getLogger(__name__)


async def delete_bar(bar_id: str) -> Dict:
    """Hard delete bar (no deleted_at on Bar)."""
    try:
        existing = await prisma.bar.find_unique(where={"id": bar_id})
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bar not found")
        await prisma.bar.delete(where={"id": bar_id})
        return create_success_response(message="Bar deleted successfully", data={"id": bar_id})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("delete_bar error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
