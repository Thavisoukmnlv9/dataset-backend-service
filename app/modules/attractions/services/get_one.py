"""Get a single attraction by ID. Uses path_to_upload_url for full image URLs."""
import logging
from typing import Any, Dict

from fastapi import HTTPException, status

from app.prisma import prisma
from app.shared.utils.responses.response import create_success_response
from app.shared.utils.upload_urls import path_to_upload_url

from app.modules.attractions.services.create import _serialize_attraction

logger = logging.getLogger(__name__)


def _apply_upload_urls(data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure cover and gallery image paths are full URLs."""
    if not data:
        return data
    if data.get("cover_image_url"):
        data["cover_image_url"] = path_to_upload_url(data["cover_image_url"])
    for g in data.get("gallery") or []:
        if g.get("url") is not None:
            g["url"] = path_to_upload_url(g["url"])
    return data


async def get_attraction_draft(attraction_id: str) -> Dict[str, Any]:
    try:
        r = await prisma.attraction.find_unique(
            where={"id": attraction_id},
            include={
                "gallery": True,
                "tags": True,
                "policies": True,
                "translations": True,
                "hours": True,
                "details": True,
                "processes": True,
            },
        )
        if not r:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
        if r.status != "DRAFT":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Attraction is not a draft")
        data = _apply_upload_urls(_serialize_attraction(r))
        return create_success_response(message="Draft retrieved successfully", data={"item": data})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_attraction_draft error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def get_attraction(attraction_id: str) -> Dict[str, Any]:
    try:
        r = await prisma.attraction.find_unique(
            where={"id": attraction_id},
            include={
                "gallery": True,
                "tags": True,
                "policies": True,
                "translations": True,
                "hours": True,
                "details": True,
                "processes": True,
            },
        )
        if not r:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attraction not found")
        data = _apply_upload_urls(_serialize_attraction(r))
        return create_success_response(message="Attraction retrieved successfully", data={"item": data})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_attraction error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
