"""List souvenirs with filters and pagination. No Qdrant/vector search."""
import logging
from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from app.prisma import prisma
from app.shared.schemas.base import PaginationParams
from app.shared.utils.responses.response import create_list_response
from app.shared.utils.upload_urls import path_to_upload_url

from app.modules.souvenirs.schemas.souvenir import SouvenirFilters

logger = logging.getLogger(__name__)


def _serialize_souvenir_list_item(s: Any) -> Dict[str, Any]:
    if not s:
        return {}
    return {
        "id": s.id,
        "category": s.category,
        "name": s.name,
        "slug": s.slug,
        "status": s.status,
        "short_description": s.short_description,
        "country": s.country,
        "province": s.province,
        "district": s.district,
        "village": s.village,
        "address_text": s.address_text,
        "latitude": s.latitude,
        "longitude": s.longitude,
        "price_band": s.price_band,
        "currency": s.currency,
        "min_price": s.min_price,
        "max_price": s.max_price,
        "cover_image_url": path_to_upload_url(s.cover_image_url),
        "rating_avg": s.rating_avg,
        "rating_count": s.rating_count or 0,
        "trust_score": s.trust_score,
        "quality_score": s.quality_score,
        "popularity_score": s.popularity_score,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        "gallery": [{"url": path_to_upload_url(g.url), "description": getattr(g, "description", None), "is_cover": getattr(g, "is_cover", False)} for g in (s.gallery or [])],
        "tags": [{"tag_type": t.tag_type, "tag_value": t.tag_value} for t in (s.tags or [])],
    }


def _build_where(filters: SouvenirFilters) -> Dict[str, Any]:
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
    return {sort_field: order}


async def get_souvenirs(
    filters: SouvenirFilters,
    pagination: PaginationParams,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    """List souvenirs with optional text search (name, description, slug)."""
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
        items = await prisma.souvenir.find_many(
            where=where,
            order=order,
            skip=pagination.skip,
            take=pagination.limit,
            include={"gallery": True, "tags": True},
        )
        total = await prisma.souvenir.count(where=where)
        serialized = [_serialize_souvenir_list_item(r) for r in items]
        return create_list_response(
            items=serialized,
            total=total,
            page=pagination.page,
            limit=pagination.limit,
            offset=pagination.offset,
            message="Souvenirs retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_souvenirs error: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
