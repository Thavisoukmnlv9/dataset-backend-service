"""Get a single restaurant by ID."""
import logging
from typing import Any, Dict

from fastapi import HTTPException, status

from app.prisma import prisma

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
        "cover_image_url": r.cover_image_url,
        "rating_avg": r.rating_avg,
        "rating_count": r.rating_count or 0,
        "trust_score": r.trust_score,
        "quality_score": r.quality_score,
        "popularity_score": r.popularity_score,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        "gallery": [{"url": g.url, "description": g.description} for g in (r.gallery or [])],
        "tags": [{"tag_type": t.tag_type, "tag_value": t.tag_value} for t in (r.tags or [])],
        "policies": [{"policy_type": p.policy_type, "policy_text": p.policy_text} for p in (r.policies or [])],
        "translations": {t.language: {"name": t.name, "short_description": t.short_description} for t in (r.translations or [])},
        "hours": {"weekly_schedule": r.hours.weekly_schedule} if r.hours else None,
        "menu": _serialize_menu(r.menu) if r.menu else None,
        "category_details": _serialize_details(r.details) if r.details else None,
    }


def _serialize_menu(m: Any) -> Any:
    if not m:
        return None
    sections = []
    for s in getattr(m, "sections", []) or []:
        items = [
            {"item_id": i.item_id, "name": i.name, "description": i.description, "price": i.price, "currency": i.currency}
            for i in (s.items or [])
        ]
        sections.append({"section_name": s.name, "items": items})
    return {
        "source_type": m.source_type,
        "source_url": m.source_url,
        "language": m.language,
        "sections": sections,
    }


def _serialize_details(d: Any) -> Any:
    """Serialize RestaurantDetails to category_details shape (restaurant.json)."""
    if not d:
        return None
    return {
        "cuisine_types": d.cuisine_types or [],
        "meal_types": d.meal_types or [],
        "avg_spend_per_person": d.avg_spend_per_person,
        "dietary_options": d.dietary_options,
        "reservation_supported": d.reservation_supported,
        "reservation_required": d.reservation_required,
        "seating_capacity": d.seating_capacity,
        "indoor_seating": d.indoor_seating,
        "outdoor_seating": d.outdoor_seating,
        "takeaway_available": d.takeaway_available,
        "delivery_available": d.delivery_available,
        "payment_methods": d.payment_methods or [],
        "signature_dishes": d.signature_dishes or [],
    }


async def get_restaurant(restaurant_id: str) -> Dict[str, Any]:
    """Get restaurant by ID."""
    from app.shared.utils.responses.response import create_success_response

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
