"""Update bar: PostgreSQL only (no Qdrant)."""
import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status, UploadFile

from app.prisma import prisma
from app.prisma.generated.fields import Json as PrismaJson
from app.shared.services.infrastructure.storage import storage_service
from app.shared.utils.responses.response import create_success_response

from app.modules.bars.schemas.bar import BarUpdate

logger = logging.getLogger(__name__)


async def update_bar(
    bar_id: str,
    data: BarUpdate,
    cover_image_file: Optional[UploadFile] = None,
    menu_source_file: Optional[UploadFile] = None,
    gallery_files: Optional[List[UploadFile]] = None,
) -> Dict[str, Any]:
    """Update bar; upload files if provided."""
    from app.modules.bars.services.create import _serialize_bar, _to_stored_path

    try:
        existing = await prisma.bar.find_unique(
            where={"id": bar_id},
            include={"gallery": True, "tags": True, "policies": True, "translations": True, "hours": True, "menu": True, "details": True},
        )
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bar not found")

        if cover_image_file and cover_image_file.filename:
            result = await storage_service.upload_file(cover_image_file, "bars")
            if result.success and result.data:
                path = _to_stored_path(result.data.get("object_name"))
                if path:
                    data.cover_image_url = path
        if menu_source_file and menu_source_file.filename and existing.menu:
            result = await storage_service.upload_file(menu_source_file, "bars/menus", auto_resize=False)
            if result.success and result.data:
                path = _to_stored_path(result.data.get("object_name"))
                if path:
                    await prisma.barmenu.update(
                        where={"id": existing.menu.id},
                        data={"source_url": path},
                    )
        if gallery_files:
            new_gallery = []
            for i, f in enumerate(gallery_files):
                if not f or not f.filename:
                    continue
                result = await storage_service.upload_file(f, "bars/gallery")
                if result.success and result.data:
                    path = _to_stored_path(result.data.get("object_name"))
                    if path:
                        new_gallery.append({"url": path, "description": None, "is_cover": i == 0})
            if new_gallery:
                await prisma.bargalleryimage.delete_many(where={"bar_id": bar_id})
                await prisma.bargalleryimage.create_many(
                    data=[{"bar_id": bar_id, "url": g["url"], "description": g.get("description"), "is_cover": g.get("is_cover", False)} for g in new_gallery]
                )

        update_payload: Dict[str, Any] = {}
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
        if data.name is not None:
            update_payload["name"] = data.name
        if data.slug is not None:
            slug_exists = await prisma.bar.find_first(where={"slug": data.slug, "id": {"not": bar_id}})
            if slug_exists:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")
            update_payload["slug"] = data.slug
        if data.status is not None:
            update_payload["status"] = data.status.value
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
        if data.languages_supported is not None:
            update_payload["languages_supported"] = [c if isinstance(c, str) else str(c) for c in data.languages_supported]
        if data.cover_image_url is not None:
            update_payload["cover_image_url"] = data.cover_image_url
        if data.rating_avg is not None:
            update_payload["rating_avg"] = data.rating_avg
        if data.rating_count is not None:
            update_payload["rating_count"] = data.rating_count
        if data.trust_score is not None:
            update_payload["trust_score"] = data.trust_score
        if data.quality_score is not None:
            update_payload["quality_score"] = data.quality_score
        if data.popularity_score is not None:
            update_payload["popularity_score"] = data.popularity_score

        if update_payload:
            await prisma.bar.update(where={"id": bar_id}, data=update_payload)

        if data.tags is not None:
            await prisma.bartag.delete_many(where={"bar_id": bar_id})
            if data.tags:
                await prisma.bartag.create_many(
                    data=[{"bar_id": bar_id, "tag_type": t.tag_type.value, "tag_value": t.tag_value} for t in data.tags]
                )
        if data.policies is not None:
            await prisma.barpolicy.delete_many(where={"bar_id": bar_id})
            if data.policies:
                await prisma.barpolicy.create_many(
                    data=[{"bar_id": bar_id, "policy_type": p.policy_type.value, "policy_text": p.policy_text} for p in data.policies]
                )
        if data.hours is not None and data.hours.weekly_schedule:
            from app.modules.bars.services.create import _to_prisma_weekly_schedule
            hours_payload: Dict[str, Any] = {"weekly_schedule": PrismaJson(_to_prisma_weekly_schedule(data.hours))}
            if getattr(data.hours, "timezone", None):
                hours_payload["timezone"] = data.hours.timezone
            if getattr(data.hours, "special_notes", None) is not None:
                hours_payload["special_notes"] = PrismaJson(data.hours.special_notes)
            if existing.hours:
                await prisma.barhours.update(
                    where={"id": existing.hours.id},
                    data=hours_payload,
                )
            else:
                await prisma.barhours.create(
                    data={"bar_id": bar_id, **hours_payload},
                )
        if data.translations is not None:
            await prisma.bartranslation.delete_many(where={"bar_id": bar_id})
            for lang, tr in data.translations.items():
                lang_str = lang.upper() if isinstance(lang, str) else str(lang).upper()
                name = tr.get("name") if isinstance(tr, dict) else getattr(tr, "name", None)
                short = tr.get("short_description") if isinstance(tr, dict) else getattr(tr, "short_description", None)
                await prisma.bartranslation.create(
                    data={"bar_id": bar_id, "language": lang_str, "name": name, "short_description": short},
                )
        if data.category_details is not None:
            cd = data.category_details
            details_payload = {
                "bar_types": cd.bar_types or [],
                "vibe_tags": cd.vibe_tags or [],
                "music_types": cd.music_types or [],
                "entertainment_types": cd.entertainment_types or [],
                "crowd_type": cd.crowd_type or [],
                "avg_spend_per_person": cd.avg_spend_per_person,
                "currency": cd.currency,
                "drink_categories": cd.drink_categories or [],
                "signature_drinks": cd.signature_drinks or [],
                "food_available": cd.food_available,
                "food_style": cd.food_style or [],
                "non_alcoholic_options": cd.non_alcoholic_options,
                "reservation_supported": cd.reservation_supported,
                "reservation_required": cd.reservation_required,
                "guestlist_supported": cd.guestlist_supported,
                "table_booking_supported": cd.table_booking_supported,
                "entry_fee": cd.entry_fee,
                "minimum_spend": cd.minimum_spend,
                "table_minimum_spend": cd.table_minimum_spend,
                "age_restriction_min": cd.age_restriction_min,
                "id_check_required": cd.id_check_required,
                "dress_code_required": cd.dress_code_required,
                "dress_code_description": cd.dress_code_description,
                "seating_capacity": cd.seating_capacity,
                "indoor_seating": cd.indoor_seating,
                "outdoor_seating": cd.outdoor_seating,
                "private_room_available": cd.private_room_available,
                "dance_floor": cd.dance_floor,
                "standing_area": cd.standing_area,
                "parking_available": cd.parking_available,
                "wifi_available": cd.wifi_available,
                "wheelchair_access": cd.wheelchair_access,
                "air_conditioned": cd.air_conditioned,
                "toilet_available": cd.toilet_available,
                "smoking_allowed": cd.smoking_allowed,
                "smoking_area_available": cd.smoking_area_available,
                "shisha_available": cd.shisha_available,
                "alcohol_served": cd.alcohol_served,
                "payment_methods": cd.payment_methods or [],
                "happy_hour_supported": cd.happy_hour_supported,
                "happy_hour_notes": cd.happy_hour_notes,
                "best_time_to_visit": cd.best_time_to_visit,
                "best_days_to_visit": cd.best_days_to_visit or [],
                "peak_hours": cd.peak_hours,
                "wait_time_peak_minutes": cd.wait_time_peak_minutes,
                "last_order_time": cd.last_order_time,
                "queue_expected": cd.queue_expected,
                "queue_peak_minutes": cd.queue_peak_minutes,
                "view_type": cd.view_type,
                "sunset_good": cd.sunset_good,
                "photo_spot": cd.photo_spot,
                "suitable_for": cd.suitable_for or [],
            }
            if existing.details:
                await prisma.bardetails.update(where={"id": existing.details.id}, data=details_payload)
            else:
                await prisma.bardetails.create(data={"bar_id": bar_id, **details_payload})

        updated = await prisma.bar.find_unique(
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
        out = _serialize_bar(updated)
        return create_success_response(message="Bar updated successfully", data={"bar": out})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("update_bar error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
