"""Get a single cafe by ID. Uses path_to_upload_url for full image URLs."""
import logging
from typing import Any, Dict

from fastapi import HTTPException, status

from app.prisma import prisma
from app.shared.utils.responses.response import create_success_response
from app.modules.cafes.services.create import _serialize_cafe

logger = logging.getLogger(__name__)


async def get_cafe(cafe_id: str) -> Dict[str, Any]:
    try:
        c = await prisma.cafe.find_unique(
            where={"id": cafe_id},
            include={
                "vendor": True,
                "tags": True,
                "hours": True,
                "media": True,
                "policies": True,
                "translations": True,
                "details": True,
                "menu": {"include": {"sections": {"include": {"items": True}}}},
                "rag_sources": {"include": {"chunks": True}},
            },
        )
        if not c:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cafe not found")
        data = _serialize_cafe(c)
        return create_success_response(message="Cafe retrieved successfully", data={"item": data})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_cafe error: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
