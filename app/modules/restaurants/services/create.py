"""
Create restaurant: PostgreSQL + Qdrant indexing with embed_text (and optional embed_image).

The API accepts multipart/form-data: a required `data` part (JSON string with the same
structure as restaurant.json) plus optional file parts (cover_image_file, menu_source_file,
gallery_0, gallery_1, ...). File placeholder keys in the JSON (cover_image_file, url_file,
source_file, image_file) should be null or omitted; actual files are sent as form fields.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status, UploadFile

from app.prisma import prisma
from app.shared.embeddings import embed_text, embed_image, EMBED_OUTPUT_DIM
from app.shared.qdrant_client import ensure_collection, upsert_points
from app.shared.utils.responses.response import create_success_response
from app.shared.services.infrastructure.storage import storage_service
from qdrant_client.models import PointStruct

from app.modules.restaurants.schemas.restaurant import (
    RestaurantCreate,
    CategoryDetailsIn,
    GalleryImageIn,
    MenuIn,
    MenuSectionIn,
    MenuItemIn,
)

logger = logging.getLogger(__name__)

QDRANT_COLLECTION = "restaurants"


def _build_searchable_text(data: RestaurantCreate) -> str:
    """Build a single text blob for embedding (name, description, tags, location)."""
    parts = [
        data.name or "",
        data.short_description or "",
        data.long_description or "",
        data.address_text or "",
        data.district or "",
        data.province or "",
        data.country or "",
    ]
    for t in data.tags or []:
        parts.append(f"{t.tag_type}: {t.tag_value}")
    if data.menu and data.menu.sections:
        for sec in data.menu.sections:
            parts.append(sec.section_name)
            for item in sec.items:
                parts.append(item.name)
                if item.description:
                    parts.append(item.description)
    return " ".join(p for p in parts if p).strip() or data.name


async def _upload_cover_image(file: Optional[UploadFile]) -> Optional[str]:
    if not file or not file.filename:
        return None
    result = await storage_service.upload_file(file, "restaurants")
    if result.success and result.data:
        return result.data.get("object_name")
    return None


async def _upload_menu_source(file: Optional[UploadFile]) -> Optional[str]:
    if not file or not file.filename:
        return None
    result = await storage_service.upload_file(file, "restaurants/menus", auto_resize=False)
    if result.success and result.data:
        return result.data.get("object_name")
    return None


async def _upload_gallery_files(files: List[UploadFile]) -> List[GalleryImageIn]:
    """Upload gallery files and return GalleryImageIn list with urls."""
    out: List[GalleryImageIn] = []
    for f in files or []:
        if not f or not f.filename:
            continue
        result = await storage_service.upload_file(f, "restaurants/gallery")
        if result.success and result.data:
            out.append(GalleryImageIn(url=result.data.get("object_name"), description=None))
    return out


def _to_prisma_languages(codes: List[Any]) -> List[str]:
    return [c.value if hasattr(c, "value") else str(c) for c in codes]


def _to_prisma_weekly_schedule(hours: Optional[Any]) -> Any:
    if not hours or not getattr(hours, "weekly_schedule", None):
        return {}
    return {k: v.model_dump() if hasattr(v, "model_dump") else v for k, v in hours.weekly_schedule.items()}


async def create_restaurant(
    data: RestaurantCreate,
    cover_image_file: Optional[UploadFile] = None,
    menu_source_file: Optional[UploadFile] = None,
    gallery_files: Optional[List[UploadFile]] = None,
) -> Dict[str, Any]:
    """
    Create restaurant in PostgreSQL and index in Qdrant.

    Expects data matching restaurant.json structure (RestaurantCreate). File uploads:
    - cover_image_file -> coverImageUrl
    - menu_source_file -> menu.sourceUrl
    - gallery_files -> gallery_urls (by order).

    Builds searchable text, embeds with embed_text, stores one point per restaurant.
    Optionally embeds cover image with embed_image and stores a second point (id = rest_id + '_cover').
    """
    now = datetime.now(timezone.utc)
    rest_id = data.id or f"rest_{now.strftime('%Y%m%d%H%M%S')}"

    # Apply file uploads
    cover_url = await _upload_cover_image(cover_image_file)
    if cover_url:
        data.cover_image_url = cover_url

    menu_source_url = await _upload_menu_source(menu_source_file)
    gallery_uploaded = await _upload_gallery_files(gallery_files or [])
    if gallery_uploaded:
        data.gallery_urls = gallery_uploaded
    if menu_source_url and data.menu:
        data.menu.source_url = menu_source_url

    try:
        async with prisma.tx() as tx:
            existing = await tx.restaurant.find_unique(where={"id": rest_id})
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Restaurant with this id already exists",
                )
            slug_exists = await tx.restaurant.find_unique(where={"slug": data.slug})
            if slug_exists:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Restaurant with this slug already exists",
                )

            # Build nested create
            create_data: Dict[str, Any] = {
                "id": rest_id,
                "category": data.category.value,
                "name": data.name,
                "slug": data.slug,
                "status": data.status.value,
                "shortDescription": data.short_description,
                "longDescription": data.long_description,
                "country": data.country,
                "province": data.province,
                "district": data.district,
                "village": data.village,
                "addressText": data.address_text,
                "latitude": data.latitude,
                "longitude": data.longitude,
                "priceBand": data.price_band.value if data.price_band else None,
                "currency": data.currency,
                "minPrice": data.min_price,
                "maxPrice": data.max_price,
                "bookingSupported": data.booking_supported,
                "walkInSupported": data.walk_in_supported,
                "languagesSupported": _to_prisma_languages(data.languages_supported),
                "coverImageUrl": data.cover_image_url,
                "ratingAvg": data.rating_avg,
                "ratingCount": data.rating_count or 0,
                "trustScore": data.trust_score,
                "qualityScore": data.quality_score,
                "popularityScore": data.popularity_score,
                "createdAt": data.created_at or now,
                "updatedAt": now,
            }

            if data.gallery_urls:
                create_data["gallery"] = {
                    "create": [
                        {"url": g.url or "", "description": g.description}
                        for g in data.gallery_urls
                    ]
                }
            if data.tags:
                create_data["tags"] = {
                    "create": [
                        {"tagType": t.tag_type.value, "tagValue": t.tag_value}
                        for t in data.tags
                    ]
                }
            if data.policies:
                create_data["policies"] = {
                    "create": [
                        {"policyType": p.policy_type.value, "policyText": p.policy_text}
                        for p in data.policies
                    ]
                }
            if data.translations:
                trans_list = []
                for lang, tr in data.translations.items():
                    name = tr.get("name") if isinstance(tr, dict) else getattr(tr, "name", None)
                    short = tr.get("short_description") if isinstance(tr, dict) else getattr(tr, "short_description", None)
                    trans_list.append({"language": lang, "name": name, "shortDescription": short})
                create_data["translations"] = {"create": trans_list}

            if data.hours and getattr(data.hours, "weekly_schedule", None):
                create_data["hours"] = {
                    "create": {"weeklySchedule": _to_prisma_weekly_schedule(data.hours)}
                }

            if data.menu:
                menu = data.menu
                sections_create = []
                for i, sec in enumerate(menu.sections or []):
                    items_create = []
                    for item in sec.items or []:
                        items_create.append({
                            "itemId": item.item_id,
                            "name": item.name,
                            "description": item.description,
                            "price": item.price,
                            "currency": item.currency,
                            "imageUrl": item.image_url,
                            "imageDescription": item.image_description,
                            "dietary": item.dietary,
                            "spiceLevel": item.spice_level.value if item.spice_level else None,
                            "allergens": item.allergens or [],
                            "tags": item.tags or [],
                        })
                    sections_create.append({
                        "name": sec.section_name,
                        "sortOrder": i,
                        "items": {"create": items_create},
                    })
                create_data["menu"] = {
                    "create": {
                        "sourceType": menu.source_type,
                        "sourceVersion": menu.source_version,
                        "sourceUrl": menu.source_url,
                        "language": menu.language.value if menu.language else None,
                        "extractedAt": menu.extracted_at,
                        "metadata": menu.metadata,
                        "sections": {"create": sections_create},
                    }
                }

            if data.category_details:
                cd = data.category_details
                create_data["details"] = {
                    "create": {
                        "cuisineTypes": cd.cuisine_types or [],
                        "mealTypes": cd.meal_types or [],
                        "avgSpendPerPerson": cd.avg_spend_per_person,
                        "dietaryOptions": cd.dietary_options,
                        "reservationSupported": cd.reservation_supported,
                        "reservationRequired": cd.reservation_required,
                        "seatingCapacity": cd.seating_capacity,
                        "indoorSeating": cd.indoor_seating,
                        "outdoorSeating": cd.outdoor_seating,
                        "takeawayAvailable": cd.takeaway_available,
                        "deliveryAvailable": cd.delivery_available,
                        "paymentMethods": cd.payment_methods or [],
                        "signatureDishes": cd.signature_dishes or [],
                    }
                }

            await tx.restaurant.create(data=create_data)

        # Index in Qdrant
        searchable_text = _build_searchable_text(data)
        if searchable_text:
            try:
                vectors = embed_text(searchable_text, task_type="RETRIEVAL_DOCUMENT", output_dimensionality=EMBED_OUTPUT_DIM)
                if vectors:
                    ensure_collection(QDRANT_COLLECTION, EMBED_OUTPUT_DIM)
                    points = [
                        PointStruct(
                            id=rest_id,
                            vector=vectors[0],
                            payload={
                                "restaurant_id": rest_id,
                                "name": data.name,
                                "slug": data.slug,
                                "type": "text",
                            },
                        )
                    ]
                    # Optional: embed cover image and add point
                    if cover_image_file and cover_image_file.file:
                        try:
                            content = await cover_image_file.read()
                            await cover_image_file.seek(0)
                            img_vec = embed_image(content, output_dimensionality=EMBED_OUTPUT_DIM)
                            points.append(
                                PointStruct(
                                    id=f"{rest_id}_cover",
                                    vector=img_vec,
                                    payload={"restaurant_id": rest_id, "name": data.name, "slug": data.slug, "type": "image"},
                                )
                            )
                        except Exception as e:
                            logger.warning("Could not embed cover image for Qdrant: %s", e)
                    upsert_points(QDRANT_COLLECTION, points)
            except Exception as e:
                logger.warning("Qdrant indexing failed (restaurant still created): %s", e)

        # Fetch created with relations for response
        created = await prisma.restaurant.find_unique(
            where={"id": rest_id},
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
        # Serialize for response (simplified)
        out = _serialize_restaurant(created) if created else {"id": rest_id}
        return create_success_response(
            message="Restaurant created successfully",
            data={"restaurant": out},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Create restaurant error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


def _serialize_restaurant(r: Any) -> Dict[str, Any]:
    """Turn Prisma restaurant model into JSON-serializable dict."""
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


def _serialize_menu(m: Any) -> Optional[Dict[str, Any]]:
    if not m:
        return None
    sections = []
    for s in getattr(m, "sections", []) or []:
        items = [{"item_id": i.itemId, "name": i.name, "description": i.description, "price": i.price, "currency": i.currency} for i in (s.items or [])]
        sections.append({"section_name": s.name, "items": items})
    return {
        "source_type": m.sourceType,
        "source_url": m.sourceUrl,
        "language": m.language,
        "sections": sections,
    }


def _serialize_details(d: Any) -> Optional[Dict[str, Any]]:
    if not d:
        return None
    return {
        "cuisine_types": d.cuisineTypes,
        "meal_types": d.mealTypes,
        "payment_methods": d.paymentMethods,
        "signature_dishes": d.signatureDishes,
    }
