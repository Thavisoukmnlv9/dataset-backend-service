"""Update cafe: PostgreSQL only (no Qdrant)."""
import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status, UploadFile

from app.prisma import prisma
from app.prisma.generated.fields import Json as PrismaJson
from app.shared.services.infrastructure.storage import storage_service
from app.shared.utils.responses.response import create_success_response

from app.modules.cafes.schemas.cafe import CafeUpdate
from app.modules.cafes.services.create import (
    _serialize_cafe,
    _to_stored_path,
    _to_prisma_weekly_schedule,
)

logger = logging.getLogger(__name__)


async def update_cafe(
    cafe_id: str,
    data: CafeUpdate,
    cover_image_file: Optional[UploadFile] = None,
    gallery_files: Optional[List[UploadFile]] = None,
    menu_source_file: Optional[UploadFile] = None,
) -> Dict[str, Any]:
    """Update cafe; upload files if provided."""
    try:
        existing = await prisma.cafe.find_unique(
            where={"id": cafe_id},
            include={
                "tags": True,
                "hours": True,
                "gallery": True,
                "policies": True,
                "translations": True,
                "details": True,
                "menu": True,
            },
        )
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cafe not found")

        if cover_image_file and getattr(cover_image_file, "filename", None):
            result = await storage_service.upload_file(cover_image_file, "cafes")
            if result.success and result.data:
                path = _to_stored_path(result.data.get("object_name"))
                if path:
                    data.cover_image_url = path
        if gallery_files:
            from app.modules.cafes.services.create import _upload_gallery_files
            gallery_uploaded = await _upload_gallery_files(gallery_files)
            if gallery_uploaded:
                existing_gallery = [{"url": g.url, "description": getattr(g, "description", None), "is_cover": getattr(g, "is_cover", False)} for g in (existing.gallery or [])]
                data.gallery_urls = existing_gallery + gallery_uploaded
        if menu_source_file and getattr(menu_source_file, "filename", None) and getattr(existing, "menu", None) and existing.menu:
            result = await storage_service.upload_file(menu_source_file, "cafes/menus", auto_resize=False)
            if result.success and result.data:
                path = _to_stored_path(result.data.get("object_name"))
                if path:
                    await prisma.cafemenu.update(
                        where={"id": existing.menu.id},
                        data={"source_url": path},
                    )

        update_payload: Dict[str, Any] = {}
        if data.name is not None:
            update_payload["name"] = data.name
        if data.slug is not None:
            slug_exists = await prisma.cafe.find_first(where={"slug": data.slug, "id": {"not": cafe_id}})
            if slug_exists:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")
            update_payload["slug"] = data.slug
        if data.vendor_name is not None:
            update_payload["vendor_name"] = data.vendor_name
        if data.contact_phone is not None:
            update_payload["contact_phone"] = data.contact_phone
        if data.whatsapp is not None:
            update_payload["whatsapp"] = data.whatsapp
        if data.email is not None:
            update_payload["email"] = data.email
        if data.verification_status is not None:
            update_payload["verification_status"] = data.verification_status.value
        if data.status is not None:
            update_payload["status"] = data.status.value
        if data.sub_category is not None:
            update_payload["sub_category"] = data.sub_category
        if data.short_description is not None:
            update_payload["short_description"] = data.short_description
        if data.long_description is not None:
            update_payload["long_description"] = data.long_description
        if data.country is not None:
            update_payload["country"] = data.country
        if data.province is not None:
            update_payload["province"] = data.province
        if data.district is not None:
            update_payload["district"] = data.district
        if data.village is not None:
            update_payload["village"] = data.village
        if data.address_text is not None:
            update_payload["address_text"] = data.address_text
        if data.latitude is not None:
            update_payload["latitude"] = data.latitude
        if data.longitude is not None:
            update_payload["longitude"] = data.longitude
        if data.price_band is not None:
            update_payload["price_band"] = data.price_band.value
        if data.currency is not None:
            update_payload["currency"] = data.currency
        if data.min_price is not None:
            update_payload["min_price"] = data.min_price
        if data.max_price is not None:
            update_payload["max_price"] = data.max_price
        if data.booking_supported is not None:
            update_payload["booking_supported"] = data.booking_supported
        if data.walk_in_supported is not None:
            update_payload["walk_in_supported"] = data.walk_in_supported
        if data.instant_confirmation is not None:
            update_payload["instant_confirmation"] = data.instant_confirmation
        if data.cancellation_policy_summary is not None:
            update_payload["cancellation_policy_summary"] = data.cancellation_policy_summary
        if data.child_friendly is not None:
            update_payload["child_friendly"] = data.child_friendly
        if data.pet_friendly is not None:
            update_payload["pet_friendly"] = data.pet_friendly
        if data.accessibility_features is not None:
            update_payload["accessibility_features"] = PrismaJson(data.accessibility_features)
        if data.languages_supported is not None:
            update_payload["languages_supported"] = [c if isinstance(c, str) else str(c) for c in data.languages_supported]
        if data.cover_image_url is not None:
            update_payload["cover_image_url"] = data.cover_image_url
        if data.gallery_urls is not None:
            await prisma.cafegalleryimage.delete_many(where={"cafe_id": cafe_id})
            if data.gallery_urls:
                await prisma.cafegalleryimage.create_many(
                    data=[
                        {
                            "cafe_id": cafe_id,
                            "url": g.get("url", "") if isinstance(g, dict) else (getattr(g, "url", None) or ""),
                            "description": g.get("description") if isinstance(g, dict) else getattr(g, "description", None),
                            "is_cover": g.get("is_cover", False) if isinstance(g, dict) else getattr(g, "is_cover", False),
                        }
                        for g in data.gallery_urls
                    ]
                )
        if data.rating_avg is not None:
            update_payload["rating_avg"] = data.rating_avg
        if data.rating_count is not None:
            update_payload["rating_count"] = data.rating_count
        if data.review_summary_text is not None:
            update_payload["review_summary_text"] = data.review_summary_text
        if data.trust_score is not None:
            update_payload["trust_score"] = data.trust_score
        if data.quality_score is not None:
            update_payload["quality_score"] = data.quality_score
        if data.popularity_score is not None:
            update_payload["popularity_score"] = data.popularity_score
        if data.last_verified_at is not None:
            update_payload["last_verified_at"] = data.last_verified_at

        if update_payload:
            await prisma.cafe.update(where={"id": cafe_id}, data=update_payload)

        if data.tags is not None:
            await prisma.cafetag.delete_many(where={"cafe_id": cafe_id})
            if data.tags:
                await prisma.cafetag.create_many(
                    data=[{"cafe_id": cafe_id, "tag_type": t.tag_type.value, "tag_value": t.tag_value} for t in data.tags]
                )
        if data.hours is not None and data.hours.weekly_schedule:
            hours_payload: Dict[str, Any] = {"weekly_schedule": PrismaJson(_to_prisma_weekly_schedule(data.hours))}
            if getattr(data.hours, "timezone", None):
                hours_payload["timezone"] = data.hours.timezone
            if getattr(data.hours, "special_notes", None) is not None:
                hours_payload["special_notes"] = PrismaJson(data.hours.special_notes)
            if existing.hours:
                await prisma.cafehours.update(where={"id": existing.hours.id}, data=hours_payload)
            else:
                await prisma.cafehours.create(data={"cafe_id": cafe_id, **hours_payload})
        if data.policies is not None:
            await prisma.cafepolicy.delete_many(where={"cafe_id": cafe_id})
            if data.policies:
                await prisma.cafepolicy.create_many(
                    data=[{"cafe_id": cafe_id, "policy_type": p.policy_type.value, "policy_text": p.policy_text} for p in data.policies]
                )
        if data.translations is not None:
            await prisma.cafetranslation.delete_many(where={"cafe_id": cafe_id})
            for lang, tr in data.translations.items():
                lang_str = lang if isinstance(lang, str) else str(lang)
                t = tr.model_dump() if hasattr(tr, "model_dump") else tr
                await prisma.cafetranslation.create(
                    data={
                        "cafe_id": cafe_id,
                        "language": lang_str,
                        "name": t.get("name"),
                        "short_description": t.get("short_description"),
                        "long_description": t.get("long_description"),
                    }
                )
        if data.category_details is not None:
            cd = data.category_details
            details_payload = {
                "cuisine_types": cd.cuisine_types or [],
                "meal_types": cd.meal_types or [],
                "avg_spend_per_person": cd.avg_spend_per_person,
                "dietary_options": PrismaJson(cd.dietary_options) if cd.dietary_options is not None else None,
                "reservation_supported": cd.reservation_supported,
                "reservation_required": cd.reservation_required,
                "seating_capacity": cd.seating_capacity,
                "indoor_seating": cd.indoor_seating,
                "outdoor_seating": cd.outdoor_seating,
                "takeaway_available": cd.takeaway_available,
                "delivery_available": cd.delivery_available,
                "payment_methods": cd.payment_methods or [],
                "signature_dishes": cd.signature_dishes or [],
                "alcohol_served": cd.alcohol_served,
                "parking_available": cd.parking_available,
                "wifi_available": cd.wifi_available,
                "noise_level": cd.noise_level,
                "suitable_for": cd.suitable_for or [],
                "best_time_to_visit": cd.best_time_to_visit,
                "wait_time_peak_minutes": cd.wait_time_peak_minutes,
                "tea_options": cd.tea_options or [],
                "coffee_styles": cd.coffee_styles or [],
            }
            if existing.details:
                await prisma.cafedetails.update(where={"id": existing.details.id}, data=details_payload)
            else:
                await prisma.cafedetails.create(data={"cafe_id": cafe_id, **details_payload})

        if data.menu is not None:
            if getattr(existing, "menu", None) and existing.menu:
                await prisma.cafemenu.delete(where={"id": existing.menu.id})
            if data.menu.sections:
                menu = data.menu
                sections_create = []
                for i, sec in enumerate(menu.sections or []):
                    items_create = []
                    for item in sec.items or []:
                        items_create.append({
                            "item_id": item.item_id,
                            "name": item.name,
                            "description": item.description,
                            "price": item.price,
                            "currency": item.currency,
                            "image_url": item.image_url,
                            "image_description": item.image_description,
                            "dietary": PrismaJson(item.dietary) if item.dietary is not None else None,
                            "spice_level": item.spice_level.value if item.spice_level else None,
                            "allergens": item.allergens or [],
                            "tags": item.tags or [],
                        })
                    sections_create.append({
                        "name": sec.section_name,
                        "source_type": sec.source_type if getattr(sec, "source_type", None) else None,
                        "sort_order": i,
                        "items": {"create": items_create},
                    })
                await prisma.cafemenu.create(
                    data={
                        "cafe_id": cafe_id,
                        "source_type": menu.source_type,
                        "source_version": menu.source_version,
                        "language": menu.language if menu.language else None,
                        "sections": {"create": sections_create},
                    }
                )

        updated = await prisma.cafe.find_unique(
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
        out = _serialize_cafe(updated)
        return create_success_response(message="Cafe updated successfully", data={"cafe": out})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("update_cafe error: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
