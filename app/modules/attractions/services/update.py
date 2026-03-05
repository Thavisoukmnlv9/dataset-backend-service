"""Update attraction: PostgreSQL only."""
import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status, UploadFile

from app.prisma import prisma
from app.prisma.generated.fields import Json as PrismaJson
from app.shared.services.infrastructure.storage import storage_service
from app.shared.utils.responses.response import create_success_response

from app.modules.attractions.schemas.attraction import AttractionUpdate

logger = logging.getLogger(__name__)


async def update_attraction(
    attraction_id: str,
    data: AttractionUpdate,
    cover_image_file: Optional[UploadFile] = None,
    gallery_files: Optional[List[UploadFile]] = None,
) -> Dict[str, Any]:
    """Update attraction; upload files if provided."""
    from app.modules.attractions.services.create import _serialize_attraction, _to_stored_path

    try:
        existing = await prisma.attraction.find_unique(
            where={"id": attraction_id},
            include={
                "gallery": True,
                "tags": True,
                "policies": True,
                "translations": True,
                "hours": True,
                "details": True,
            },
        )
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attraction not found")

        if cover_image_file and cover_image_file.filename:
            result = await storage_service.upload_file(cover_image_file, "attractions")
            if result.success and result.data:
                path = _to_stored_path(result.data.get("object_name"))
                if path:
                    data.cover_image_url = path
        if gallery_files:
            new_gallery = []
            for i, f in enumerate(gallery_files):
                if not f or not f.filename:
                    continue
                result = await storage_service.upload_file(f, "attractions/gallery")
                if result.success and result.data:
                    path = _to_stored_path(result.data.get("object_name"))
                    if path:
                        new_gallery.append({"url": path, "description": None, "is_cover": i == 0})
            if new_gallery:
                await prisma.attractiongalleryimage.delete_many(where={"attraction_id": attraction_id})
                await prisma.attractiongalleryimage.create_many(
                    data=[
                        {
                            "attraction_id": attraction_id,
                            "url": g["url"],
                            "description": g.get("description"),
                            "is_cover": g.get("is_cover", False),
                        }
                        for g in new_gallery
                    ]
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
            slug_exists = await prisma.attraction.find_first(
                where={"slug": data.slug, "id": {"not": attraction_id}}
            )
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
            update_payload["languages_supported"] = [
                c if isinstance(c, str) else str(c) for c in data.languages_supported
            ]
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
            await prisma.attraction.update(where={"id": attraction_id}, data=update_payload)

        if data.tags is not None:
            await prisma.attractiontag.delete_many(where={"attraction_id": attraction_id})
            if data.tags:
                await prisma.attractiontag.create_many(
                    data=[
                        {
                            "attraction_id": attraction_id,
                            "tag_type": t.tag_type,
                            "tag_value": t.tag_value,
                        }
                        for t in data.tags
                    ]
                )
        if data.policies is not None:
            await prisma.attractionpolicy.delete_many(where={"attraction_id": attraction_id})
            if data.policies:
                await prisma.attractionpolicy.create_many(
                    data=[
                        {
                            "attraction_id": attraction_id,
                            "policy_type": p.policy_type.value,
                            "policy_text": p.policy_text,
                        }
                        for p in data.policies
                    ]
                )
        if data.hours is not None and data.hours.weekly_schedule:
            from app.modules.attractions.services.create import _to_prisma_weekly_schedule

            hours_payload: Dict[str, Any] = {
                "weekly_schedule": PrismaJson(_to_prisma_weekly_schedule(data.hours))
            }
            if getattr(data.hours, "timezone", None):
                hours_payload["timezone"] = data.hours.timezone
            if getattr(data.hours, "special_notes", None) is not None:
                hours_payload["special_notes"] = PrismaJson(data.hours.special_notes)
            if existing.hours:
                await prisma.attractionhours.update(
                    where={"id": existing.hours.id},
                    data=hours_payload,
                )
            else:
                await prisma.attractionhours.create(
                    data={"attraction_id": attraction_id, **hours_payload},
                )
        if data.translations is not None:
            await prisma.attractiontranslation.delete_many(where={"attraction_id": attraction_id})
            for lang, tr in data.translations.items():
                lang_str = lang.upper() if isinstance(lang, str) else str(lang).upper()
                name = tr.get("name") if isinstance(tr, dict) else getattr(tr, "name", None)
                short = tr.get("short_description") if isinstance(tr, dict) else getattr(tr, "short_description", None)
                await prisma.attractiontranslation.create(
                    data={
                        "attraction_id": attraction_id,
                        "language": lang_str,
                        "name": name,
                        "short_description": short,
                    },
                )
        if data.details is not None:
            dd = data.details
            details_payload = {
                "attraction_type": dd.attraction_type or [],
                "ownership_type": dd.ownership_type or [],
                "entry_fee_adult": dd.entry_fee_adult,
                "entry_fee_child": dd.entry_fee_child,
                "ticketing_type": dd.ticketing_type or "GENERAL",
                "recommended_visit_duration_minutes": dd.recommended_visit_duration_minutes,
                "best_visit_time": dd.best_visit_time or "",
                "seasonality": dd.seasonality or "",
                "weather_dependency": dd.weather_dependency or "",
                "difficulty_level": dd.difficulty_level or "",
                "walking_required": dd.walking_required,
                "stairs_required": dd.stairs_required,
                "wheelchair_access": dd.wheelchair_access,
                "family_friendly": dd.family_friendly,
                "guide_available": dd.guide_available,
                "photo_spot": dd.photo_spot,
                "swim_allowed": dd.swim_allowed,
                "dress_code_required": dd.dress_code_required,
                "dress_code_description": dd.dress_code_description,
                "safety_notes": dd.safety_notes,
                "facilities": PrismaJson(dd.facilities) if dd.facilities is not None else None,
                "travel_time_from_city_center_minutes": dd.travel_time_from_city_center_minutes,
                "combo_with": dd.combo_with or [],
                "dietary_options": PrismaJson(dd.dietary_options) if dd.dietary_options is not None else None,
                "reservation_supported": dd.reservation_supported,
                "reservation_required": dd.reservation_required,
                "payment_methods": dd.payment_methods or [],
                "alcohol_served": dd.alcohol_served,
                "parking_available": dd.parking_available,
                "wifi_available": dd.wifi_available,
                "noise_level": dd.noise_level,
            }
            if existing.details:
                await prisma.attractiondetails.update(
                    where={"id": existing.details.id},
                    data=details_payload,
                )
            else:
                await prisma.attractiondetails.create(
                    data={"attraction_id": attraction_id, **details_payload},
                )

        updated = await prisma.attraction.find_unique(
            where={"id": attraction_id},
            include={
                "gallery": True,
                "tags": True,
                "policies": True,
                "translations": True,
                "hours": True,
                "details": True,
            },
        )
        out = _serialize_attraction(updated)
        return create_success_response(message="Attraction updated successfully", data={"attraction": out})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("update_attraction error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
