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
) -> Dict[str, Any]:
    """Update cafe; upload files if provided."""
    try:
        existing = await prisma.cafe.find_unique(
            where={"id": cafe_id},
            include={
                "vendor": True,
                "tags": True,
                "hours": True,
                "media": True,
                "policies": True,
                "translations": True,
                "details": True,
                "rag_sources": {"include": {"chunks": True}},
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
            new_urls: List[str] = []
            for f in gallery_files:
                if not f or not getattr(f, "filename", None):
                    continue
                result = await storage_service.upload_file(f, "cafes/gallery")
                if result.success and result.data:
                    path = _to_stored_path(result.data.get("object_name"))
                    if path:
                        new_urls.append(path)
            if new_urls:
                data.gallery_urls = list(existing.gallery_urls or []) + new_urls

        update_payload: Dict[str, Any] = {}
        if data.name is not None:
            update_payload["name"] = data.name
        if data.slug is not None:
            slug_exists = await prisma.cafe.find_first(where={"slug": data.slug, "id": {"not": cafe_id}})
            if slug_exists:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")
            update_payload["slug"] = data.slug
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
            update_payload["gallery_urls"] = data.gallery_urls
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
            if existing.hours:
                await prisma.cafehours.update(where={"id": existing.hours.id}, data=hours_payload)
            else:
                await prisma.cafehours.create(data={"cafe_id": cafe_id, **hours_payload})
        if data.media is not None:
            await prisma.cafemedia.delete_many(where={"cafe_id": cafe_id})
            if data.media:
                await prisma.cafemedia.create_many(
                    data=[
                        {
                            "cafe_id": cafe_id,
                            "media_type": m.media_type,
                            "url": m.url,
                            "caption": m.caption,
                            "sort_order": m.sort_order,
                            "source": m.source,
                            "is_verified": m.is_verified,
                        }
                        for m in data.media
                    ]
                )
        if data.policies is not None:
            await prisma.cafepolicy.delete_many(where={"cafe_id": cafe_id})
            if data.policies:
                await prisma.cafepolicy.create_many(
                    data=[
                        {
                            "cafe_id": cafe_id,
                            "policy_type": p.policy_type.value,
                            "policy_text": p.policy_text,
                            "structured_policy": PrismaJson(p.structured_policy) if p.structured_policy is not None else None,
                        }
                        for p in data.policies
                    ]
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
                "cafe_type": cd.cafe_type,
                "coffee_styles": cd.coffee_styles or [],
                "tea_options": cd.tea_options,
                "dessert_available": cd.dessert_available,
                "avg_spend_per_person": cd.avg_spend_per_person,
                "wifi_quality": cd.wifi_quality,
                "power_outlets_available": cd.power_outlets_available,
                "work_friendly": cd.work_friendly,
                "quiet_level": cd.quiet_level,
                "stay_duration_friendly": cd.stay_duration_friendly,
                "air_conditioning": cd.air_conditioning,
                "smoking_area": cd.smoking_area,
                "opening_early": cd.opening_early,
                "late_open": cd.late_open,
                "instagrammable_score": cd.instagrammable_score,
                "view_type": cd.view_type,
            }
            if existing.details:
                await prisma.cafedetails.update(where={"id": existing.details.id}, data=details_payload)
            else:
                await prisma.cafedetails.create(data={"cafe_id": cafe_id, **details_payload})
        if data.rag_sources is not None:
            await prisma.ragsource.delete_many(where={"cafe_id": cafe_id})
            for rs in data.rag_sources:
                rag = await prisma.ragsource.create(
                    data={
                        "document_id": rs.document_id,
                        "cafe_id": cafe_id,
                        "source_type": rs.source_type,
                        "language": rs.language,
                    },
                )
                if rs.chunks:
                    await prisma.ragchunk.create_many(
                        data=[
                            {
                                "rag_source_id": rag.id,
                                "chunk_id": ch.chunk_id,
                                "chunk_type": ch.chunk_type,
                                "chunk_text": ch.chunk_text,
                            }
                            for ch in rs.chunks
                        ]
                    )

        updated = await prisma.cafe.find_unique(
            where={"id": cafe_id},
            include={
                "vendor": True,
                "tags": True,
                "hours": True,
                "media": True,
                "policies": True,
                "translations": True,
                "details": True,
                "rag_sources": {"include": {"chunks": True}},
            },
        )
        out = _serialize_cafe(updated)
        return create_success_response(message="Cafe updated successfully", data={"cafe": out})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("update_cafe error: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
