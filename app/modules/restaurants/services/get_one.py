"""Get a single restaurant by ID."""
import logging
from typing import Any, Dict
from fastapi import HTTPException, status
from app.prisma import prisma
from app.shared.utils.responses.response import create_success_response
from app.modules.restaurants.services.create import _serialize_restaurant

logger = logging.getLogger(__name__)


async def get_restaurant(restaurant_id: str) -> Dict[str, Any]:
    try:
        r = await prisma.restaurant.find_unique(
            where={"id": restaurant_id},
            include={
                "gallery": True,
                "tags": True,
                "policies": True,
                "translations": True,
                "hours": True,
                "menu": {"include": {"sections": {"include": {"items": True}}}},
                "details": True,
            },
        )
        if not r:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")
        data = _serialize_restaurant(r)
        return create_success_response(message="Restaurant retrieved successfully", data={"item": data})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_restaurant error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
