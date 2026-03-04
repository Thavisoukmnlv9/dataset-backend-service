import logging
import re
import uuid
from datetime import datetime, timezone, date
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status, UploadFile
from app.prisma import prisma
from app.prisma.generated.fields import Json as PrismaJson
from app.shared.embeddings import embed_text_or_fallback, EMBED_OUTPUT_DIM
from app.shared.qdrant_client import ensure_collection, upsert_points
from app.shared.utils.responses.response import create_success_response
from app.shared.utils.upload_urls import path_to_upload_url
from app.shared.services.infrastructure.storage import storage_service
from qdrant_client.models import PointStruct

from app.modules.restaurants.schemas.restaurant import (
    RestaurantCreate,
    GalleryImageIn,
)

logger = logging.getLogger(__name__)

QDRANT_COLLECTION = "restaurants"


def _payload_for_qdrant(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Copy payload and remove cover_image_url, image_url, url so they are not stored in Qdrant."""
    FIELDS_TO_DROP = frozenset({"cover_image_url", "image_url", "url"})

    def drop_keys(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: drop_keys(v) for k, v in obj.items() if k not in FIELDS_TO_DROP}
        if isinstance(obj, list):
            return [drop_keys(x) for x in obj]
        return obj

    return drop_keys(payload) if payload else {}


def _to_json_safe(obj: Any) -> Any:
    """Convert payload to JSON-serializable types for Qdrant (enums, datetime, etc.)."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (datetime, date)):
        return obj.isoformat() if hasattr(obj, "isoformat") else str(obj)
    if isinstance(obj, dict):
        return {str(k): _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_json_safe(x) for x in obj]
    return str(obj)


def _build_searchable_text_from_record(r: Any) -> str:
    """Build searchable text from a Prisma restaurant record (for sync to Qdrant)."""
    if not r:
        return ""
    parts = [
        r.name or "",
        r.short_description or "",
        r.long_description or "",
        r.address_text or "",
        r.district or "",
        r.province or "",
        r.country or "",
    ]
    for t in (r.tags or []):
        parts.append(f"{t.tag_type}: {t.tag_value}")
    if r.menu and getattr(r.menu, "sections", None):
        for s in r.menu.sections or []:
            parts.append(s.name)
            for i in getattr(s, "items", []) or []:
                parts.append(i.name)
                if getattr(i, "description", None):
                    parts.append(i.description)
    return " ".join(p for p in parts if p).strip() or (r.name or str(r.id))


# Path prefix stored in Prisma for uploaded files (e.g. /uploads/restaurants/menu_items/...)
UPLOADS_PREFIX = "/uploads"


def _to_stored_path(object_name: Optional[str]) -> Optional[str]:
    """Convert storage object_name to path stored in Prisma: /uploads/restaurants/..."""
    if not object_name or not object_name.strip():
        return None
    s = object_name.strip().lstrip("/")
    if not s:
        return None
    if s.startswith("uploads/"):
        return "/" + s
    return f"{UPLOADS_PREFIX}/{s}"


def _slugify(text: str) -> str:
    """Generate URL-safe slug from name."""
    if not text or not text.strip():
        return "restaurant-" + uuid.uuid4().hex[:8]
    s = re.sub(r"[^a-z0-9]+", "-", text.lower().strip()).strip("-")
    return s or "restaurant-" + uuid.uuid4().hex[:8]


async def _resolve_slug(tx: Any, slug: Optional[str], name: str) -> str:
    """Return slug to use; if slug is None/empty, generate from name and ensure unique."""
    base = (slug or "").strip() or _slugify(name)
    candidate = base
    n = 0
    while True:
        existing = await tx.restaurant.find_unique(where={"slug": candidate})
        if not existing:
            return candidate
        n += 1
        candidate = f"{base}-{n}"


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
        logger.debug("No cover image file provided (file=%s, filename=%s)", bool(
            file), getattr(file, "filename", None))
        return None
    try:
        if hasattr(file, "file") and file.file is not None and hasattr(file.file, "seek"):
            file.file.seek(0)
        result = await storage_service.upload_file(file, "restaurants")
    except Exception as e:
        logger.warning("Cover image upload failed: %s", e)
        return None
    if not result.success:
        logger.warning("Cover image upload returned success=False")
        return None
    data = result.data or {}
    object_name = data.get("object_name")
    if object_name:
        path = _to_stored_path(object_name)
        if path:
            return path
    url = data.get("url")
    if url and isinstance(url, str) and url.strip().startswith("/"):
        return url.strip() if not url.strip().startswith("//") else url.strip()
    logger.warning(
        "Cover image upload gave no object_name or usable url: data=%s", list(data.keys()))
    return None


async def _upload_menu_source(file: Optional[UploadFile]) -> Optional[str]:
    if not file or not file.filename:
        return None
    result = await storage_service.upload_file(file, "restaurants/menus", auto_resize=False)
    if result.success and result.data:
        return _to_stored_path(result.data.get("object_name"))
    return None


async def _upload_gallery_files(files: List[UploadFile]) -> List[GalleryImageIn]:
    """Upload gallery files and return GalleryImageIn list with urls."""
    out: List[GalleryImageIn] = []
    for f in files or []:
        if not f or not f.filename:
            continue
        result = await storage_service.upload_file(f, "restaurants/gallery")
        if result.success and result.data:
            url = _to_stored_path(result.data.get("object_name"))
            if url:
                out.append(GalleryImageIn(url=url, description=None))
    return out


async def _upload_single_file(file: UploadFile, path_prefix: str) -> Optional[str]:
    """Upload one file to path_prefix and return path for Prisma (/uploads/...), or None."""
    if not file or not file.filename:
        return None
    result = await storage_service.upload_file(file, path_prefix)
    if result.success and result.data:
        return _to_stored_path(result.data.get("object_name"))
    return None


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
    menu_item_files: Optional[Dict[Tuple[int, int], List[UploadFile]]] = None,
) -> Dict[str, Any]:

    cover_url = await _upload_cover_image(cover_image_file)
    if cover_url:
        data.cover_image_url = cover_url

    menu_source_url = await _upload_menu_source(menu_source_file)
    gallery_uploaded = await _upload_gallery_files(gallery_files or [])
    if gallery_uploaded:
        if data.gallery_urls and len(data.gallery_urls) >= len(gallery_uploaded):
            for i, gu in enumerate(gallery_uploaded):
                data.gallery_urls[i].url = gu.url
        else:
            data.gallery_urls = gallery_uploaded
    if menu_source_url and data.menu:
        data.menu.source_url = menu_source_url

    if menu_item_files and data.menu and data.menu.sections:
        for (sec_idx, item_idx), files in sorted(menu_item_files.items()):
            if not files or sec_idx >= len(data.menu.sections) or item_idx >= len(data.menu.sections[sec_idx].items):
                continue
            item = data.menu.sections[sec_idx].items[item_idx]
            existing = list(item.image_url) if item.image_url else []
            new_urls = []
            for f in files:
                url = await _upload_single_file(f, "restaurants/menu_items")
                if url:
                    new_urls.append(url)
            if new_urls:
                item.image_url = existing + new_urls
    
    try:
        async with prisma.tx() as tx:
            resolved_slug = await _resolve_slug(tx, data.slug, data.name)

            create_data: Dict[str, Any] = {
                "category": data.category.value,
                "name": data.name,
                "slug": resolved_slug,
                "status": data.status.value,
                "vendor_name": data.vendor_name,
                "contact_phone": data.contact_phone,
                "whatsapp": data.whatsapp,
                "email": data.email,
                "verification_status": data.verification_status.value if data.verification_status else None,
                "short_description": data.short_description,
                "long_description": data.long_description,
                "country": data.country,
                "province": data.province,
                "district": data.district,
                "village": data.village,
                "address_text": data.address_text,
                "latitude": data.latitude,
                "longitude": data.longitude,
                "price_band": data.price_band.value if data.price_band else None,
                "currency": data.currency,
                "min_price": data.min_price,
                "max_price": data.max_price,
                "booking_supported": data.booking_supported,
                "walk_in_supported": data.walk_in_supported,
                "languages_supported": _to_prisma_languages(data.languages_supported),
                "cover_image_url": data.cover_image_url,
                "rating_avg": data.rating_avg,
                "rating_count": data.rating_count or 0,
                "trust_score": data.trust_score,
                "quality_score": data.quality_score,
                "popularity_score": data.popularity_score,
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
                        {"tag_type": t.tag_type.value, "tag_value": t.tag_value}
                        for t in data.tags
                    ]
                }
            if data.policies:
                create_data["policies"] = {
                    "create": [
                        {"policy_type": p.policy_type.value,
                            "policy_text": p.policy_text}
                        for p in data.policies
                    ]
                }
            if data.translations:
                trans_list = []
                for lang, tr in data.translations.items():
                    lang_str = lang.upper() if isinstance(lang, str) else str(lang).upper()
                    name = tr.get("name") if isinstance(
                        tr, dict) else getattr(tr, "name", None)
                    short = tr.get("short_description") if isinstance(
                        tr, dict) else getattr(tr, "short_description", None)
                    trans_list.append(
                        {"language": lang_str, "name": name, "short_description": short})
                if trans_list:
                    create_data["translations"] = {"create": trans_list}

            if data.hours and getattr(data.hours, "weekly_schedule", None):
                hours_payload: Dict[str, Any] = {
                    "weekly_schedule": PrismaJson(_to_prisma_weekly_schedule(data.hours))
                }
                if getattr(data.hours, "timezone", None):
                    hours_payload["timezone"] = data.hours.timezone
                if getattr(data.hours, "special_notes", None) is not None:
                    hours_payload["special_notes"] = PrismaJson(data.hours.special_notes)
                create_data["hours"] = {"create": hours_payload}

            if data.menu:
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
                create_data["menu"] = {
                    "create": {
                        "source_type": menu.source_type,
                        "source_version": menu.source_version,
                        "language": menu.language if menu.language else None,
                        "sections": {"create": sections_create},
                    }
                }

            if data.category_details:
                cd = data.category_details
                create_data["details"] = {
                    "create": {
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
                    }
                }

            created_in_tx = await tx.restaurant.create(data=create_data)
            rest_id = created_in_tx.id

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
        full_payload = _serialize_restaurant(
            created) if created else {"id": rest_id}

        searchable_text = _build_searchable_text(data)
        if not searchable_text:
            searchable_text = data.name or str(rest_id)
        try:
            vectors = embed_text_or_fallback(
                searchable_text,
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=EMBED_OUTPUT_DIM,
            )
            if vectors:
                ensure_collection(QDRANT_COLLECTION, EMBED_OUTPUT_DIM)
                qdrant_payload = _to_json_safe(
                    {**_payload_for_qdrant(full_payload), "type": "text"})
                text_point_payload = qdrant_payload
                points = [
                    PointStruct(
                        id=rest_id,
                        vector=vectors[0],
                        payload=text_point_payload,
                    )
                ]
                upsert_points(QDRANT_COLLECTION, points)
                logger.info("Restaurant %s indexed in Qdrant (RAG)", rest_id)
        except Exception as e:
            logger.exception(
                "Qdrant indexing failed (restaurant created in PostgreSQL): %s", e)

        return create_success_response(
            message="Restaurant created successfully",
            data={"restaurant": full_payload},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Create restaurant error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


async def sync_restaurants_to_qdrant() -> Dict[str, Any]:
    """
    Duplicate all restaurants from PostgreSQL into Qdrant (backfill).
    Uses same payload shape as create (full document, minus cover_image_url/image_url/url).
    """
    try:
        restaurants = await prisma.restaurant.find_many(
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
        if not restaurants:
            return create_success_response(
                message="No restaurants to sync",
                data={"synced": 0, "total": 0},
            )
        ensure_collection(QDRANT_COLLECTION, EMBED_OUTPUT_DIM)
        synced = 0
        for r in restaurants:
            try:
                searchable = _build_searchable_text_from_record(r)
                vectors = embed_text_or_fallback(
                    searchable,
                    task_type="RETRIEVAL_DOCUMENT",
                    output_dimensionality=EMBED_OUTPUT_DIM,
                )
                if vectors:
                    full = _serialize_restaurant(r)
                    qdrant_payload = _to_json_safe(
                        {**_payload_for_qdrant(full), "type": "text"})
                    upsert_points(
                        QDRANT_COLLECTION,
                        [
                            PointStruct(
                                id=r.id,
                                vector=vectors[0],
                                payload=qdrant_payload,
                            )
                        ],
                    )
                    synced += 1
            except Exception as e:
                logger.warning(
                    "Qdrant sync failed for restaurant %s: %s", r.id, e)
        return create_success_response(
            message="Restaurants synced to Qdrant",
            data={"synced": synced, "total": len(restaurants)},
        )
    except Exception as e:
        logger.exception("sync_restaurants_to_qdrant error: %s", e)
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
        "vendor_name": getattr(r, "vendor_name", None),
        "contact_phone": getattr(r, "contact_phone", None),
        "whatsapp": getattr(r, "whatsapp", None),
        "email": getattr(r, "email", None),
        "verification_status": getattr(r, "verification_status", None),
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
        "gallery": [{"url": path_to_upload_url(g.url), "description": g.description} for g in (r.gallery or [])],
        "tags": [{"tag_type": t.tag_type, "tag_value": t.tag_value} for t in (r.tags or [])],
        "policies": [{"policy_type": p.policy_type, "policy_text": p.policy_text} for p in (r.policies or [])],
        "translations": {t.language: {"name": t.name, "short_description": t.short_description} for t in (r.translations or [])},
        "hours": {"timezone": getattr(r.hours, "timezone", None), "weekly_schedule": r.hours.weekly_schedule, "special_notes": getattr(r.hours, "special_notes", None)} if r.hours else None,
        "menu": _serialize_menu(r.menu) if r.menu else None,
        "category_details": _serialize_details(r.details) if r.details else None,
    }


def _serialize_menu(m: Any) -> Optional[Dict[str, Any]]:
    if not m:
        return None
    sections = []
    for s in getattr(m, "sections", []) or []:
        items = []
        for i in (s.items or []):
            item = {
                "item_id": i.item_id,
                "name": i.name,
                "description": i.description,
                "price": i.price,
                "currency": i.currency,
            }
            item["image_url"] = [path_to_upload_url(u) for u in (getattr(i, "image_url", None) or [])]
            if getattr(i, "image_description", None) is not None:
                item["image_description"] = i.image_description
            if getattr(i, "dietary", None) is not None:
                item["dietary"] = i.dietary
            if getattr(i, "spice_level", None) is not None:
                item["spice_level"] = i.spice_level
            if getattr(i, "allergens", None) is not None:
                item["allergens"] = i.allergens or []
            if getattr(i, "tags", None) is not None:
                item["tags"] = i.tags or []
            items.append(item)
        sections.append({"section_name": s.name, "source_type": getattr(s, "source_type", None), "items": items})
    return {
        "source_type": m.source_type,
        "source_url": path_to_upload_url(getattr(m, "source_url", None)) or "",
        "language": m.language,
        "sections": sections,
    }


def _serialize_details(d: Any) -> Optional[Dict[str, Any]]:
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
        "alcohol_served": getattr(d, "alcohol_served", False),
        "parking_available": getattr(d, "parking_available", False),
        "wifi_available": getattr(d, "wifi_available", False),
        "noise_level": getattr(d, "noise_level", None),
        "suitable_for": getattr(d, "suitable_for", None) or [],
        "best_time_to_visit": getattr(d, "best_time_to_visit", None),
        "wait_time_peak_minutes": getattr(d, "wait_time_peak_minutes", None),
    }
