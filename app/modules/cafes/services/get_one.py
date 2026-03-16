"""Get a single cafe by ID. Uses path_to_upload_url for full image URLs (same as Restaurant)."""
import logging
from typing import Any, Dict

from fastapi import HTTPException, status

from app.prisma import prisma
from app.shared.utils.responses.response import create_success_response
from app.shared.utils.upload_urls import path_to_upload_url
from app.modules.cafes.services.create import _serialize_cafe

logger = logging.getLogger(__name__)


def _apply_upload_urls(data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure cover, gallery, and menu image paths are full URLs."""
    if not data:
        return data
    if data.get("cover_image_url"):
        data["cover_image_url"] = path_to_upload_url(data["cover_image_url"])
    for g in data.get("gallery") or []:
        if g.get("url") is not None:
            g["url"] = path_to_upload_url(g["url"])
    menu = data.get("menu")
    if menu:
        if menu.get("source_url"):
            menu["source_url"] = path_to_upload_url(menu["source_url"]) or ""
        for sec in menu.get("sections") or []:
            for item in sec.get("items") or []:
                if item.get("image_url") is not None:
                    item["image_url"] = [path_to_upload_url(u) for u in (item["image_url"] or [])]
    return data


async def get_cafe_draft(cafe_id: str) -> Dict[str, Any]:
    try:
        c = await prisma.cafe.find_unique(
            where={"id": cafe_id},
            include={
                "tags": True,
                "hours": True,
                "gallery": True,
                "policies": True,
                "translations": True,
                "details": True,
                "menu": {"include": {"sections": {"include": {"items": True}}}},
            },
        )
        if not c:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
        if c.status != "DRAFT":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cafe is not a draft")
        data = _apply_upload_urls(_serialize_cafe(c))
        return create_success_response(message="Draft retrieved successfully", data={"item": data})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_cafe_draft error: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def get_cafe(cafe_id: str) -> Dict[str, Any]:
    try:
        c = await prisma.cafe.find_unique(
            where={"id": cafe_id},
            include={
                "tags": True,
                "hours": True,
                "gallery": True,
                "policies": True,
                "translations": True,
                "details": True,
                "menu": {"include": {"sections": {"include": {"items": True}}}},
            },
        )
        if not c:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cafe not found")
        data = _apply_upload_urls(_serialize_cafe(c))
        return create_success_response(message="Cafe retrieved successfully", data={"item": data})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_cafe error: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
