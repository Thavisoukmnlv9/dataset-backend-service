"""List cafes with filters and pagination. No Qdrant/vector search."""
import logging
from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from app.prisma import prisma
from app.shared.schemas.base import PaginationParams
from app.shared.utils.responses.response import create_list_response
from app.shared.utils.upload_urls import path_to_upload_url

from app.modules.cafes.schemas.cafe import CafeFilters

logger = logging.getLogger(__name__)


def _serialize_cafe_list_item(c: Any) -> Dict[str, Any]:
    if not c:
        return {}
    return {
        "id": c.id,
        "listing_id": getattr(c, "listing_id", None),
        "category": c.category,
        "sub_category": getattr(c, "sub_category", None),
        "name": c.name,
        "slug": c.slug,
        "status": c.status,
        "short_description": c.short_description,
        "country": c.country,
        "province": c.province,
        "district": c.district,
        "village": c.village,
        "address_text": c.address_text,
        "latitude": c.latitude,
        "longitude": c.longitude,
        "price_band": c.price_band,
        "currency": c.currency,
        "min_price": c.min_price,
        "max_price": c.max_price,
        "cover_image_url": path_to_upload_url(c.cover_image_url),
        "rating_avg": c.rating_avg,
        "rating_count": c.rating_count or 0,
        "trust_score": c.trust_score,
        "quality_score": c.quality_score,
        "popularity_score": c.popularity_score,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        "gallery": [{"url": path_to_upload_url(g.url), "description": getattr(g, "description", None), "is_cover": getattr(g, "is_cover", False)} for g in (c.gallery or [])],
        "tags": [{"tag_type": t.tag_type, "tag_value": t.tag_value} for t in (c.tags or [])],
    }


def _build_where(filters: CafeFilters) -> Dict[str, Any]:
    where: Dict[str, Any] = {}
    if filters.province:
        where["province"] = {"equals": filters.province, "mode": "insensitive"}
    if filters.district:
        where["district"] = {"equals": filters.district, "mode": "insensitive"}
    if filters.status:
        where["status"] = filters.status.value
    if filters.category is not None:
        where["category"] = filters.category.value
    if filters.sub_category:
        where["sub_category"] = {"equals": filters.sub_category, "mode": "insensitive"}
    return where


def _order_clause(sort: Optional[str], order: str) -> Dict[str, str]:
    sort_field = sort or "created_at"
    return {sort_field: order}


async def get_cafes(
    filters: CafeFilters,
    pagination: PaginationParams,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    """List cafes with optional text search (name, description, slug)."""
    try:
        where = _build_where(filters)
        if search and search.strip():
            where["OR"] = [
                {"name": {"contains": search.strip(), "mode": "insensitive"}},
                {"short_description": {"contains": search.strip(), "mode": "insensitive"}},
                {"long_description": {"contains": search.strip(), "mode": "insensitive"}},
                {"slug": {"contains": search.strip(), "mode": "insensitive"}},
            ]
        order = _order_clause(pagination.sort, pagination.order)
        items = await prisma.cafe.find_many(
            where=where,
            order=order,
            skip=pagination.skip,
            take=pagination.limit,
            include={"gallery": True, "tags": True},
        )
        total = await prisma.cafe.count(where=where)
        serialized = [_serialize_cafe_list_item(r) for r in items]
        return create_list_response(
            items=serialized,
            total=total,
            page=pagination.page,
            limit=pagination.limit,
            offset=pagination.offset,
            message="Cafes retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_cafes error: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
