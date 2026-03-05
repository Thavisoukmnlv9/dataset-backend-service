"""List attractions with filters and pagination."""
import logging
from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from app.prisma import prisma
from app.shared.schemas.base import PaginationParams
from app.shared.utils.responses.response import create_list_response
from app.shared.utils.upload_urls import path_to_upload_url

from app.modules.attractions.schemas.attraction import AttractionFilters

logger = logging.getLogger(__name__)


def _serialize_attraction_for_list(r: Any) -> Dict[str, Any]:
    if not r:
        return {}
    return {
        "id": r.id,
        "category": r.category,
        "name": r.name,
        "slug": r.slug,
        "status": r.status,
        "short_description": r.short_description,
        "long_description": r.long_description,
        "country": r.country,
        "province": r.province,
        "district": r.district,
        "village": r.village,
        "address_text": r.address_text,
        "latitude": r.latitude,
        "longitude": r.longitude,
        "price_band": r.price_band,
        "currency": r.currency,
        "min_price": r.min_price,
        "max_price": r.max_price,
        "booking_supported": r.booking_supported,
        "walk_in_supported": r.walk_in_supported,
        "languages_supported": r.languages_supported or [],
        "cover_image_url": path_to_upload_url(r.cover_image_url),
        "rating_avg": r.rating_avg,
        "rating_count": r.rating_count or 0,
        "trust_score": r.trust_score,
        "quality_score": r.quality_score,
        "popularity_score": r.popularity_score,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        "gallery": [
            {"url": path_to_upload_url(g.url), "description": g.description, "is_cover": getattr(g, "is_cover", False)}
            for g in (r.gallery or [])
        ],
        "tags": [{"tag_type": t.tag_type, "tag_value": t.tag_value} for t in (r.tags or [])],
    }


def _build_where(filters: AttractionFilters) -> Dict[str, Any]:
    where: Dict[str, Any] = {}
    if filters.province:
        where["province"] = {"equals": filters.province, "mode": "insensitive"}
    if filters.district:
        where["district"] = {"equals": filters.district, "mode": "insensitive"}
    if filters.status:
        where["status"] = filters.status.value
    if filters.category:
        where["category"] = {"equals": filters.category, "mode": "insensitive"}
    return where


def _order_clause(sort: Optional[str], order: str) -> Dict[str, str]:
    sort_field = sort or "created_at"
    if sort_field:
        return {sort_field: order}
    return {"created_at": "desc"}


async def get_attractions(
    filters: AttractionFilters,
    pagination: PaginationParams,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    """List attractions with optional text search (name, description, slug)."""
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
        items = await prisma.attraction.find_many(
            where=where,
            order=order,
            skip=pagination.skip,
            take=pagination.limit,
            include={"gallery": True, "tags": True},
        )
        total = await prisma.attraction.count(where=where)
        serialized = [_serialize_attraction_for_list(r) for r in items]
        return create_list_response(
            items=serialized,
            total=total,
            page=pagination.page,
            limit=pagination.limit,
            offset=pagination.offset,
            message="Attractions retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_attractions error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
