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
        "short_description": getattr(r, "shortDescription", None),
        "long_description": getattr(r, "longDescription", None),
        "country": r.country,
        "province": r.province,
        "district": r.district,
        "village": r.village,
        "address_text": getattr(r, "addressText", None),
        "latitude": r.latitude,
        "longitude": r.longitude,
        "price_band": getattr(r, "priceBand", None),
        "currency": r.currency,
        "min_price": getattr(r, "minPrice", None),
        "max_price": getattr(r, "maxPrice", None),
        "booking_supported": getattr(r, "bookingSupported", None),
        "walk_in_supported": getattr(r, "walkInSupported", None),
        "languages_supported": getattr(r, "languagesSupported", []),
        "cover_image_url": getattr(r, "coverImageUrl", None),
        "rating_avg": getattr(r, "ratingAvg", None),
        "rating_count": getattr(r, "ratingCount", 0),
        "trust_score": getattr(r, "trustScore", None),
        "quality_score": getattr(r, "qualityScore", None),
        "popularity_score": getattr(r, "popularityScore", None),
        "created_at": r.createdAt.isoformat() if getattr(r, "createdAt", None) else None,
        "updated_at": r.updatedAt.isoformat() if getattr(r, "updatedAt", None) else None,
        "gallery": [{"url": g.url, "description": g.description} for g in (r.gallery or [])],
        "tags": [{"tag_type": t.tagType, "tag_value": t.tagValue} for t in (r.tags or [])],
        "policies": [{"policy_type": p.policyType, "policy_text": p.policyText} for p in (r.policies or [])],
        "translations": {t.language: {"name": t.name, "short_description": t.shortDescription} for t in (r.translations or [])},
        "hours": {"weekly_schedule": r.hours.weeklySchedule} if r.hours else None,
        "menu": _serialize_menu(r.menu) if r.menu else None,
        "details": _serialize_details(r.details) if r.details else None,
    }


def _serialize_menu(m: Any) -> Any:
    if not m:
        return None
    sections = []
    for s in getattr(m, "sections", []) or []:
        items = [
            {"item_id": i.itemId, "name": i.name, "description": i.description, "price": i.price, "currency": i.currency}
            for i in (s.items or [])
        ]
        sections.append({"section_name": s.name, "items": items})
    return {
        "source_type": m.sourceType,
        "source_url": m.sourceUrl,
        "language": m.language,
        "sections": sections,
    }


def _serialize_details(d: Any) -> Any:
    if not d:
        return None
    return {
        "cuisine_types": d.cuisineTypes,
        "meal_types": d.mealTypes,
        "payment_methods": d.paymentMethods,
        "signature_dishes": d.signatureDishes,
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
