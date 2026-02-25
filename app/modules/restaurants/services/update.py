"""Update restaurant: PostgreSQL and optional re-index in Qdrant."""
import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status, UploadFile

from app.prisma import prisma
from app.prisma.generated.fields import Json as PrismaJson
from app.shared.services.infrastructure.storage import storage_service
from app.shared.utils.responses.response import create_success_response

from app.modules.restaurants.schemas.restaurant import LanguageCodeEnum, RestaurantUpdate

logger = logging.getLogger(__name__)


async def update_restaurant(
    restaurant_id: str,
    data: RestaurantUpdate,
    cover_image_file: Optional[UploadFile] = None,
    menu_source_file: Optional[UploadFile] = None,
    gallery_files: Optional[List[UploadFile]] = None,
) -> Dict[str, Any]:
    """Update restaurant; upload files if provided and re-index in Qdrant if searchable content changed."""
    from app.modules.restaurants.services.create import _serialize_restaurant, _to_stored_path

    try:
        existing = await prisma.restaurant.find_unique(
            where={"id": restaurant_id},
            include={"gallery": True, "tags": True, "policies": True, "translations": True, "hours": True, "menu": True, "details": True},
        )
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Restaurant not found")

        # Upload files and set URLs (stored in Prisma as /uploads/...)
        if cover_image_file and cover_image_file.filename:
            result = await storage_service.upload_file(cover_image_file, "restaurants")
            if result.success and result.data:
                path = _to_stored_path(result.data.get("object_name"))
                if path:
                    data.cover_image_url = path
        if menu_source_file and menu_source_file.filename and existing.menu:
            result = await storage_service.upload_file(menu_source_file, "restaurants/menus", auto_resize=False)
            if result.success and result.data:
                path = _to_stored_path(result.data.get("object_name"))
                if path:
                    await prisma.restaurantmenu.update(
                        where={"id": existing.menu.id},
                        data={"source_url": path},
                    )
        if gallery_files:
            new_gallery = []
            for f in gallery_files:
                if not f or not f.filename:
                    continue
                result = await storage_service.upload_file(f, "restaurants/gallery")
                if result.success and result.data:
                    path = _to_stored_path(result.data.get("object_name"))
                    if path:
                        new_gallery.append({"url": path, "description": None})
            if new_gallery:
                await prisma.restaurantgalleryimage.delete_many(where={"restaurant_id": restaurant_id})
                await prisma.restaurantgalleryimage.create_many(
                    data=[{"restaurant_id": restaurant_id, "url": g["url"], "description": g.get("description")} for g in new_gallery]
                )

        # Build update payload (only set provided fields)
        update_payload: Dict[str, Any] = {}
        if data.name is not None:
            update_payload["name"] = data.name
        if data.slug is not None:
            slug_exists = await prisma.restaurant.find_first(where={"slug": data.slug, "id": {"not": restaurant_id}})
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
            update_payload["languages_supported"] = [c.value for c in data.languages_supported]
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
            await prisma.restaurant.update(where={"id": restaurant_id}, data=update_payload)

        # Tags, policies, hours, menu, details: simplified - only replace if provided
        if data.tags is not None:
            await prisma.restauranttag.delete_many(where={"restaurant_id": restaurant_id})
            if data.tags:
                await prisma.restauranttag.create_many(
                    data=[{"restaurant_id": restaurant_id, "tag_type": t.tag_type.value, "tag_value": t.tag_value} for t in data.tags]
                )
        if data.policies is not None:
            await prisma.restaurantpolicy.delete_many(where={"restaurant_id": restaurant_id})
            if data.policies:
                await prisma.restaurantpolicy.create_many(
                    data=[{"restaurant_id": restaurant_id, "policy_type": p.policy_type.value, "policy_text": p.policy_text} for p in data.policies]
                )
        if data.hours is not None and data.hours.weekly_schedule:
            from app.modules.restaurants.services.create import _to_prisma_weekly_schedule
            hours_json = PrismaJson(_to_prisma_weekly_schedule(data.hours))
            if existing.hours:
                await prisma.restauranthours.update(
                    where={"id": existing.hours.id},
                    data={"weekly_schedule": hours_json},
                )
            else:
                await prisma.restauranthours.create(
                    data={"restaurant_id": restaurant_id, "weekly_schedule": hours_json},
                )
        if data.translations is not None:
            await prisma.restauranttranslation.delete_many(where={"restaurant_id": restaurant_id})
            for lang, tr in data.translations.items():
                lang_str = lang.upper() if isinstance(lang, str) else lang
                try:
                    lang_enum = LanguageCodeEnum(lang_str)
                except ValueError:
                    continue
                name = tr.get("name") if isinstance(tr, dict) else getattr(tr, "name", None)
                short = tr.get("short_description") if isinstance(tr, dict) else getattr(tr, "short_description", None)
                await prisma.restauranttranslation.create(
                    data={"restaurant_id": restaurant_id, "language": lang_enum.value, "name": name, "short_description": short},
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
            }
            if existing.details:
                await prisma.restaurantdetails.update(where={"id": existing.details.id}, data=details_payload)
            else:
                await prisma.restaurantdetails.create(data={"restaurant_id": restaurant_id, **details_payload})

        # Re-index in Qdrant with full restaurant data (no fields cut; for RAG)
        updated = await prisma.restaurant.find_unique(
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
        if updated:
            try:
                from app.modules.restaurants.services.create import QDRANT_COLLECTION
                from app.shared.embeddings import embed_text_or_fallback, EMBED_OUTPUT_DIM
                from app.shared.qdrant_client import ensure_collection, upsert_points
                from qdrant_client.models import PointStruct

                parts = [
                    updated.name or "",
                    updated.short_description or "",
                    updated.long_description or "",
                    updated.address_text or "",
                    updated.district or "",
                    updated.province or "",
                    updated.country or "",
                ]
                for t in updated.tags or []:
                    parts.append(f"{t.tag_type}: {t.tag_value}")
                if updated.menu and updated.menu.sections:
                    for s in updated.menu.sections:
                        parts.append(s.name)
                        for i in s.items or []:
                            parts.append(i.name)
                            if i.description:
                                parts.append(i.description)
                searchable = " ".join(p for p in parts if p).strip() or updated.name or restaurant_id
                vectors = embed_text_or_fallback(searchable, task_type="RETRIEVAL_DOCUMENT", output_dimensionality=EMBED_OUTPUT_DIM)
                if vectors:
                    ensure_collection(QDRANT_COLLECTION, EMBED_OUTPUT_DIM)
                    from app.modules.restaurants.services.create import _payload_for_qdrant
                    qdrant_payload = {**_payload_for_qdrant(_serialize_restaurant(updated)), "type": "text"}
                    upsert_points(
                        QDRANT_COLLECTION,
                        [
                            PointStruct(
                                id=restaurant_id,
                                vector=vectors[0],
                                payload=qdrant_payload,
                            )
                        ],
                    )
                    logger.info("Restaurant %s re-indexed in Qdrant (RAG)", restaurant_id)
            except Exception as e:
                logger.warning("Qdrant re-index on update failed: %s", e)

        out = _serialize_restaurant(
            await prisma.restaurant.find_unique(
                where={"id": restaurant_id},
                include={"gallery": True, "tags": True, "policies": True, "translations": True, "hours": True, "menu": {"include": {"sections": {"include": {"items": True}}}}, "details": True},
            )
        )
        return create_success_response(message="Restaurant updated successfully", data={"restaurant": out})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("update_restaurant error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
