"""Get a single souvenir by ID. Uses path_to_upload_url for full image URLs."""
import logging
from typing import Any, Dict

from fastapi import HTTPException, status

from app.prisma import prisma
from app.shared.utils.responses.response import create_success_response
from app.shared.utils.upload_urls import path_to_upload_url
from app.modules.souvenirs.services.create import _serialize_souvenir

logger = logging.getLogger(__name__)


def _apply_upload_urls(data: Dict[str, Any]) -> Dict[str, Any]:
    if not data:
        return data
    for g in data.get("gallery") or []:
        if g.get("url") is not None:
            g["url"] = path_to_upload_url(g["url"])
    for p in data.get("products") or []:
        for img in p.get("images") or []:
            if img.get("url") is not None:
                img["url"] = path_to_upload_url(img["url"])
    return data


async def get_souvenir(souvenir_id: str) -> Dict[str, Any]:
    try:
        s = await prisma.souvenir.find_unique(
            where={"id": souvenir_id},
            include={
                "tags": True,
                "hours": True,
                "gallery": True,
                "policies": True,
                "translations": True,
                "details": True,
                "products": {"include": {"images": True}},
            },
        )
        if not s:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Souvenir not found")
        data = _apply_upload_urls(_serialize_souvenir(s))
        return create_success_response(message="Souvenir retrieved successfully", data={"item": data})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_souvenir error: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
