"""List restaurants with filters and pagination. Optional: vector search via Qdrant."""
import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.prisma import prisma
from app.shared.schemas.base import PaginationParams
from app.shared.utils.responses.response import create_list_response
from app.shared.utils.upload_urls import path_to_upload_url

from app.modules.restaurants.schemas.restaurant import RestaurantFilters

logger = logging.getLogger(__name__)


def _serialize_restaurant(r: Any) -> Dict[str, Any]:
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
        "gallery": [{"url": path_to_upload_url(g.url), "description": g.description, "is_cover": getattr(g, "is_cover", False)} for g in (r.gallery or [])],
        "tags": [{"tag_type": t.tag_type, "tag_value": t.tag_value} for t in (r.tags or [])],
    }


def _build_where(filters: RestaurantFilters) -> Dict[str, Any]:
    where: Dict[str, Any] = {}
    if filters.province:
        where["province"] = {"equals": filters.province, "mode": "insensitive"}
    if filters.district:
        where["district"] = {"equals": filters.district, "mode": "insensitive"}
    if filters.status:
        where["status"] = filters.status.value
    if filters.category:
        where["category"] = filters.category.value
    return where


def _order_clause(sort: Optional[str], order: str) -> Dict[str, str]:
    sort_field = sort or "created_at"
    if sort_field:
        return {sort_field: order}
    return {"created_at": "desc"}


async def get_restaurants(
    filters: RestaurantFilters,
    pagination: PaginationParams,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    """List restaurants with optional text search (name, description, slug)."""
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
        items = await prisma.restaurant.find_many(
            where=where,
            order=order,
            skip=pagination.skip,
            take=pagination.limit,
            include={"gallery": True, "tags": True},
        )
        total = await prisma.restaurant.count(where=where)
        serialized = [_serialize_restaurant(r) for r in items]
        return create_list_response(
            items=serialized,
            total=total,
            page=pagination.page,
            limit=pagination.limit,
            offset=pagination.offset,
            message="Restaurants retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_restaurants error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def search_restaurants_vector(query: str, limit: int = 20) -> Dict[str, Any]:
    """
    Semantic search: embed query with RETRIEVAL_QUERY, search Qdrant, return restaurant IDs
    then load full records from PostgreSQL.
    """
    from app.shared.embeddings import embed_text, EMBED_OUTPUT_DIM
    from app.shared.qdrant_client import get_qdrant_client

    try:
        vectors = embed_text(query, task_type="RETRIEVAL_QUERY", output_dimensionality=EMBED_OUTPUT_DIM)
        if not vectors:
            return create_list_response(items=[], total=0, page=1, limit=limit, offset=0, message="No results")
        client = get_qdrant_client()
        results = client.search(
            collection_name="restaurants",
            query_vector=vectors[0],
            limit=limit,
            with_payload=True,
        )
        ids = []
        for hit in results:
            rid = hit.payload.get("restaurant_id") if hit.payload else hit.id
            if rid and rid not in ids:
                ids.append(rid)
        if not ids:
            return create_list_response(items=[], total=0, page=1, limit=limit, offset=0, message="No results")
        # Load from DB
        restaurants = await prisma.restaurant.find_many(
            where={"id": {"in": ids}},
            include={"gallery": True, "tags": True},
        )
        by_id = {r.id: r for r in restaurants}
        ordered = [by_id[i] for i in ids if i in by_id]
        serialized = [_serialize_restaurant(r) for r in ordered]
        return create_list_response(
            items=serialized,
            total=len(serialized),
            page=1,
            limit=limit,
            offset=0,
            message="Vector search completed",
        )
    except Exception as e:
        logger.exception("search_restaurants_vector error: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
