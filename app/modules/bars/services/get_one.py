"""Get a single bar by ID. Uses path_to_upload_url for full image URLs."""
import logging
from typing import Any, Dict

from fastapi import HTTPException, status

from app.prisma import prisma
from app.shared.utils.responses.response import create_success_response
from app.shared.utils.upload_urls import path_to_upload_url
from app.modules.bars.services.create import _serialize_bar

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


async def get_bar(bar_id: str) -> Dict[str, Any]:
    try:
        r = await prisma.bar.find_unique(
            where={"id": bar_id},
            include={
                "gallery": True,
                "tags": True,
                "policies": True,
                "translations": True,
                "hours": True,
                "menu": {"include": {"barMenuSections": {"include": {"items": True}}}},
                "details": True,
            },
        )
        if not r:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bar not found")
        data = _apply_upload_urls(_serialize_bar(r))
        return create_success_response(message="Bar retrieved successfully", data={"item": data})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_bar error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
