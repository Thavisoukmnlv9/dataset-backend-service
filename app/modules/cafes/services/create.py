"""Create cafe: Cafe + details, tags, hours, media, policies, translations, rag_sources. No Qdrant."""
import logging
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status, UploadFile

from app.prisma import prisma
from app.prisma.generated.fields import Json as PrismaJson
from app.shared.utils.responses.response import create_success_response
from app.shared.utils.upload_urls import path_to_upload_url
from app.shared.services.infrastructure.storage import storage_service

from app.modules.cafes.schemas.cafe import (
    CafeCreate,
    GalleryImageIn,
)

logger = logging.getLogger(__name__)

UPLOADS_PREFIX = "/uploads"


def _to_stored_path(object_name: Optional[str]) -> Optional[str]:
    if not object_name or not object_name.strip():
        return None
    s = object_name.strip().lstrip("/")
    if not s:
        return None
    if s.startswith("uploads/"):
        return "/" + s
    return f"{UPLOADS_PREFIX}/{s}"


def _slugify(text: str) -> str:
    if not text or not text.strip():
        return "cafe-" + uuid.uuid4().hex[:8]
    s = re.sub(r"[^a-z0-9]+", "-", text.lower().strip()).strip("-")
    return s or "cafe-" + uuid.uuid4().hex[:8]


async def _resolve_slug(tx: Any, slug: Optional[str], name: str) -> str:
    base = (slug or "").strip() or _slugify(name)
    candidate = base
    n = 0
    while True:
        existing = await tx.cafe.find_unique(where={"slug": candidate})
        if not existing:
            return candidate
        n += 1
        candidate = f"{base}-{n}"


async def _upload_cover_image(file: Optional[UploadFile]) -> Optional[str]:
    if not file or not getattr(file, "filename", None):
        return None
    try:
        if hasattr(file, "file") and file.file is not None and hasattr(file.file, "seek"):
            file.file.seek(0)
        result = await storage_service.upload_file(file, "cafes")
    except Exception as e:
        logger.warning("Cover image upload failed: %s", e)
        return None
    if not result.success or not result.data:
        return None
    object_name = result.data.get("object_name")
    if object_name:
        return _to_stored_path(object_name)
    url = result.data.get("url")
    if url and isinstance(url, str) and url.strip().startswith("/"):
        return url.strip()
    return None


async def _upload_gallery_files(files: List[UploadFile]) -> List[GalleryImageIn]:
    """Upload gallery files and return GalleryImageIn list with urls (same as Restaurant)."""
    out: List[GalleryImageIn] = []
    for f in files or []:
        if not f or not getattr(f, "filename", None):
            continue
        result = await storage_service.upload_file(f, "cafes/gallery")
        if result.success and result.data:
            path = _to_stored_path(result.data.get("object_name"))
            if path:
                out.append(GalleryImageIn(url=path, description=None))
    return out


def _serialize_cafe(c: Any) -> Dict[str, Any]:
    """Turn Prisma cafe model into JSON-serializable dict."""
    if not c:
        return {}
    return {
        "id": c.id,
        "listing_id": getattr(c, "listing_id", None),
        "vendor_name": getattr(c, "vendor_name", None),
        "contact_phone": getattr(c, "contact_phone", None),
        "whatsapp": getattr(c, "whatsapp", None),
        "email": getattr(c, "email", None),
        "verification_status": getattr(c, "verification_status", None),
        "category": c.category,
        "sub_category": getattr(c, "sub_category", None),
        "name": c.name,
        "slug": c.slug,
        "status": c.status,
        "short_description": c.short_description,
        "long_description": c.long_description,
        "country": c.country,
        "province": c.province,
        "district": c.district,
        "village": c.village,
        "address_text": c.address_text,
        "latitude": c.latitude,
        "longitude": c.longitude,
        "price_band": c.price_band,
        "currency": c.currency,
        "min_price": c.min_price,
        "max_price": c.max_price,
        "booking_supported": c.booking_supported,
        "walk_in_supported": c.walk_in_supported,
        "instant_confirmation": getattr(c, "instant_confirmation", False),
        "cancellation_policy_summary": getattr(c, "cancellation_policy_summary", None),
        "child_friendly": c.child_friendly,
        "pet_friendly": c.pet_friendly,
        "accessibility_features": getattr(c, "accessibility_features", None),
        "languages_supported": c.languages_supported or [],
        "cover_image_url": path_to_upload_url(c.cover_image_url),
        "gallery": [{"url": path_to_upload_url(g.url), "description": getattr(g, "description", None), "is_cover": getattr(g, "is_cover", False)} for g in (c.gallery or [])],
        "rating_avg": c.rating_avg,
        "rating_count": c.rating_count or 0,
        "review_summary_text": getattr(c, "review_summary_text", None),
        "trust_score": c.trust_score,
        "quality_score": c.quality_score,
        "popularity_score": c.popularity_score,
        "last_verified_at": c.last_verified_at.isoformat() if getattr(c, "last_verified_at", None) else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        "tags": [{"tag_type": t.tag_type, "tag_value": t.tag_value} for t in (c.tags or [])],
        "hours": _serialize_hours(c.hours) if c.hours else None,
        "policies": [_serialize_policy(p) for p in (c.policies or [])],
        "translations": {t.language: {"name": t.name, "short_description": t.short_description, "long_description": getattr(t, "long_description", None)} for t in (c.translations or [])},
        "category_details": _serialize_details(c.details) if c.details else None,
        "menu": _serialize_cafe_menu(c.menu) if getattr(c, "menu", None) else None,
    }


def _serialize_hours(h: Any) -> Optional[Dict[str, Any]]:
    if not h:
        return None
    return {
        "timezone": h.timezone,
        "weekly_schedule": h.weekly_schedule,
        "special_notes": getattr(h, "special_notes", None),
    }


def _serialize_policy(p: Any) -> Dict[str, Any]:
    if not p:
        return {}
    return {
        "policy_type": p.policy_type,
        "policy_text": p.policy_text,
    }


def _serialize_details(d: Any) -> Optional[Dict[str, Any]]:
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
        "tea_options": getattr(d, "tea_options", None) or [],
        "coffee_styles": getattr(d, "coffee_styles", None) or [],
    }


def _serialize_cafe_menu(m: Any) -> Optional[Dict[str, Any]]:
    if not m:
        return None
    sections = []
    for s in getattr(m, "sections", []) or []:
        items = []
        for i in (getattr(s, "items", None) or []):
            item = {
                "item_id": getattr(i, "item_id", None),
                "name": i.name,
                "description": getattr(i, "description", None),
                "price": getattr(i, "price", None),
                "currency": getattr(i, "currency", None),
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
        sections.append({
            "section_name": s.name,
            "source_type": getattr(s, "source_type", None),
            "items": items,
        })
    return {
        "source_type": m.source_type,
        "source_url": path_to_upload_url(getattr(m, "source_url", None)) or "",
        "language": getattr(m, "language", None),
        "sections": sections,
    }


def _to_prisma_weekly_schedule(hours: Optional[Any]) -> Any:
    if not hours or not getattr(hours, "weekly_schedule", None):
        return {}
    return {k: v.model_dump() if hasattr(v, "model_dump") else v for k, v in hours.weekly_schedule.items()}


async def create_cafe(
    data: CafeCreate,
    cover_image_file: Optional[UploadFile] = None,
    gallery_files: Optional[List[UploadFile]] = None,
    menu_source_file: Optional[UploadFile] = None,
    menu_item_files: Optional[Dict[Tuple[int, int], List[UploadFile]]] = None,
) -> Dict[str, Any]:
    """Create cafe using inline vendor fields (vendor_name, contact_phone, etc.)."""
    cover_url = await _upload_cover_image(cover_image_file)
    if cover_url:
        data.cover_image_url = cover_url
    gallery_uploaded = await _upload_gallery_files(gallery_files or [])
    if gallery_uploaded:
        # Merge is_cover and description from gallery_files metadata (same as Restaurant)
        metadata_list = data.gallery_files or []
        for i, gu in enumerate(gallery_uploaded):
            if i < len(metadata_list):
                meta = metadata_list[i]
                gu.is_cover = getattr(meta, "is_cover", False)
                if getattr(meta, "description", None) is not None:
                    gu.description = meta.description
        if data.gallery_urls and len(data.gallery_urls) >= len(gallery_uploaded):
            for i, gu in enumerate(gallery_uploaded):
                data.gallery_urls[i].url = gu.url
                data.gallery_urls[i].is_cover = gu.is_cover
                if gu.description is not None:
                    data.gallery_urls[i].description = gu.description
        else:
            data.gallery_urls = gallery_uploaded
        if not cover_url and data.cover_image_url is None:
            for g in data.gallery_urls:
                if getattr(g, "is_cover", False) and g.url:
                    data.cover_image_url = g.url
                    break

    async def _upload_menu_source(file: Optional[UploadFile]) -> Optional[str]:
        if not file or not getattr(file, "filename", None):
            return None
        result = await storage_service.upload_file(file, "cafes/menus", auto_resize=False)
        if result.success and result.data:
            return _to_stored_path(result.data.get("object_name"))
        return None

    async def _upload_single_file(file: UploadFile, path_prefix: str) -> Optional[str]:
        if not file or not getattr(file, "filename", None):
            return None
        result = await storage_service.upload_file(file, path_prefix)
        if result.success and result.data:
            return _to_stored_path(result.data.get("object_name"))
        return None

    menu_source_url = await _upload_menu_source(menu_source_file)
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
                url = await _upload_single_file(f, "cafes/menu_items")
                if url:
                    new_urls.append(url)
            if new_urls:
                item.image_url = existing + new_urls

    try:
        async with prisma.tx() as tx:
            resolved_slug = await _resolve_slug(tx, data.slug, data.name)
            create_data: Dict[str, Any] = {
                "listing_id": data.listing_id,
                "vendor_name": data.vendor_name,
                "contact_phone": data.contact_phone,
                "whatsapp": data.whatsapp,
                "email": data.email,
                "verification_status": data.verification_status.value if data.verification_status else None,
                "category": data.category.value,
                "sub_category": data.sub_category,
                "name": data.name,
                "slug": resolved_slug,
                "status": data.status.value,
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
                "instant_confirmation": data.instant_confirmation,
                "cancellation_policy_summary": data.cancellation_policy_summary,
                "child_friendly": data.child_friendly,
                "pet_friendly": data.pet_friendly,
                "accessibility_features": PrismaJson(data.accessibility_features) if data.accessibility_features is not None else None,
                "languages_supported": [c if isinstance(c, str) else str(c) for c in (data.languages_supported or [])],
                "cover_image_url": data.cover_image_url,
                "rating_avg": data.rating_avg,
                "rating_count": data.rating_count or 0,
                "review_summary_text": data.review_summary_text,
                "trust_score": data.trust_score,
                "quality_score": data.quality_score,
                "popularity_score": data.popularity_score,
                "last_verified_at": data.last_verified_at,
            }
            if data.gallery_urls:
                gallery_list = []
                for g in data.gallery_urls:
                    if isinstance(g, dict):
                        url = g.get("url") or ""
                        desc = g.get("description")
                        is_cover = g.get("is_cover", False)
                    else:
                        url = getattr(g, "url", None) or ""
                        desc = getattr(g, "description", None)
                        is_cover = getattr(g, "is_cover", False)
                    gallery_list.append({"url": url, "description": desc, "is_cover": is_cover})
                create_data["gallery"] = {"create": gallery_list}
            if data.tags:
                create_data["tags"] = {
                    "create": [{"tag_type": t.tag_type.value, "tag_value": t.tag_value} for t in data.tags]
                }
            if data.hours and getattr(data.hours, "weekly_schedule", None):
                hours_payload: Dict[str, Any] = {
                    "timezone": getattr(data.hours, "timezone", None),
                    "weekly_schedule": PrismaJson(_to_prisma_weekly_schedule(data.hours)),
                }
                if getattr(data.hours, "special_notes", None) is not None:
                    hours_payload["special_notes"] = PrismaJson(data.hours.special_notes)
                create_data["hours"] = {"create": hours_payload}
            if data.policies:
                create_data["policies"] = {
                    "create": [{"policy_type": p.policy_type.value, "policy_text": p.policy_text} for p in data.policies]
                }
            if data.translations:
                trans_list = []
                for lang, tr in data.translations.items():
                    lang_str = lang if isinstance(lang, str) else str(lang)
                    t = tr if isinstance(tr, dict) else tr.model_dump()
                    trans_list.append({
                        "language": lang_str,
                        "name": t.get("name"),
                        "short_description": t.get("short_description"),
                        "long_description": t.get("long_description"),
                    })
                if trans_list:
                    create_data["translations"] = {"create": trans_list}
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
                        "tea_options": cd.tea_options or [],
                        "coffee_styles": cd.coffee_styles or [],
                    }
                }
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
                        "source_url": menu.source_url,
                        "language": menu.language if menu.language else None,
                        "sections": {"create": sections_create},
                    }
                }
            created_in_tx = await tx.cafe.create(data=create_data)
            cafe_id = created_in_tx.id

        created = await prisma.cafe.find_unique(
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
        full_payload = _serialize_cafe(created) if created else {"id": cafe_id}
        return create_success_response(
            message="Cafe created successfully",
            data={"cafe": full_payload},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Create cafe error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
