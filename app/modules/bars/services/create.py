import logging
import re
import uuid
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status, UploadFile
from app.prisma import prisma
from app.prisma.generated.fields import Json as PrismaJson
from app.shared.utils.responses.response import create_success_response
from app.shared.utils.upload_urls import path_to_upload_url
from app.shared.services.infrastructure.storage import storage_service

from app.modules.bars.schemas.bar import (
    BarCreate,
    GalleryImageIn,
)

logger = logging.getLogger(__name__)

UPLOADS_PREFIX = "/uploads"


def _to_stored_path(object_name: Optional[str]) -> Optional[str]:
    """Convert storage object_name to path stored in Prisma: /uploads/bars/..."""
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
        return "bar-" + uuid.uuid4().hex[:8]
    s = re.sub(r"[^a-z0-9]+", "-", text.lower().strip()).strip("-")
    return s or "bar-" + uuid.uuid4().hex[:8]


async def _resolve_slug(tx: Any, slug: Optional[str], name: str) -> str:
    """Return slug to use; if slug is None/empty, generate from name and ensure unique."""
    base = (slug or "").strip() or _slugify(name)
    candidate = base
    n = 0
    while True:
        existing = await tx.bar.find_unique(where={"slug": candidate})
        if not existing:
            return candidate
        n += 1
        candidate = f"{base}-{n}"


async def _upload_cover_image(file: Optional[UploadFile]) -> Optional[str]:
    if not file or not file.filename:
        return None
    try:
        if hasattr(file, "file") and file.file is not None and hasattr(file.file, "seek"):
            file.file.seek(0)
        result = await storage_service.upload_file(file, "bars")
    except Exception as e:
        logger.warning("Cover image upload failed: %s", e)
        return None
    if not result.success:
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
    return None


async def _upload_menu_source(file: Optional[UploadFile]) -> Optional[str]:
    if not file or not file.filename:
        return None
    result = await storage_service.upload_file(file, "bars/menus", auto_resize=False)
    if result.success and result.data:
        return _to_stored_path(result.data.get("object_name"))
    return None


async def _upload_gallery_files(files: List[UploadFile]) -> List[GalleryImageIn]:
    out: List[GalleryImageIn] = []
    for f in files or []:
        if not f or not f.filename:
            continue
        result = await storage_service.upload_file(f, "bars/gallery")
        if result.success and result.data:
            url = _to_stored_path(result.data.get("object_name"))
            if url:
                out.append(GalleryImageIn(url=url, description=None))
    return out


async def _upload_single_file(file: UploadFile, path_prefix: str) -> Optional[str]:
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


async def create_bar(
    data: BarCreate,
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
                url = await _upload_single_file(f, "bars/menu_items")
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
                        {"url": g.url or "", "description": g.description, "is_cover": getattr(g, "is_cover", False)}
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
                        {"policy_type": p.policy_type.value, "policy_text": p.policy_text}
                        for p in data.policies
                    ]
                }
            if data.translations:
                trans_list = []
                for lang, tr in data.translations.items():
                    lang_str = lang.upper() if isinstance(lang, str) else str(lang).upper()
                    name = tr.get("name") if isinstance(tr, dict) else getattr(tr, "name", None)
                    short = tr.get("short_description") if isinstance(tr, dict) else getattr(tr, "short_description", None)
                    trans_list.append({"language": lang_str, "name": name, "short_description": short})
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
                            "name": item.name,
                            "description": item.description,
                            "price": item.price,
                            "currency": item.currency,
                            "image_url": item.image_url,
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
                        "source_url": getattr(menu, "source_url", None),
                        "language": menu.language if menu.language else None,
                        "barMenuSections": {"create": sections_create},
                    }
                }

            if data.category_details:
                cd = data.category_details
                create_data["details"] = {
                    "create": {
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
                        "dietary_options": PrismaJson(cd.dietary_options) if cd.dietary_options is not None else None,
                    }
                }

            created_in_tx = await tx.bar.create(data=create_data)
            bar_id = created_in_tx.id

        created = await prisma.bar.find_unique(
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
        full_payload = _serialize_bar(created) if created else {"id": bar_id}

        return create_success_response(
            message="Bar created successfully",
            data={"bar": full_payload},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Create bar error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


def _serialize_bar(r: Any) -> Dict[str, Any]:
    """Turn Prisma bar model into JSON-serializable dict."""
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
        "gallery": [{"url": path_to_upload_url(g.url), "description": g.description, "is_cover": getattr(g, "is_cover", False)} for g in (r.gallery or [])],
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
    sections = getattr(m, "barMenuSections", None) or getattr(m, "sections", []) or []
    out_sections = []
    for s in sections:
        items = []
        for i in (s.items or []):
            item = {
                "item_id": getattr(i, "item_id", None),
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
        out_sections.append({"section_name": s.name, "source_type": getattr(s, "source_type", None), "items": items})
    return {
        "source_type": m.source_type,
        "source_url": path_to_upload_url(getattr(m, "source_url", None)) or "",
        "language": m.language,
        "sections": out_sections,
    }


def _serialize_details(d: Any) -> Optional[Dict[str, Any]]:
    if not d:
        return None
    return {
        "bar_types": getattr(d, "bar_types", None) or [],
        "vibe_tags": getattr(d, "vibe_tags", None) or [],
        "music_types": getattr(d, "music_types", None) or [],
        "entertainment_types": getattr(d, "entertainment_types", None) or [],
        "crowd_type": getattr(d, "crowd_type", None) or [],
        "avg_spend_per_person": getattr(d, "avg_spend_per_person", None),
        "currency": getattr(d, "currency", None),
        "drink_categories": getattr(d, "drink_categories", None) or [],
        "signature_drinks": getattr(d, "signature_drinks", None) or [],
        "food_available": getattr(d, "food_available", False),
        "food_style": getattr(d, "food_style", None) or [],
        "non_alcoholic_options": getattr(d, "non_alcoholic_options", False),
        "reservation_supported": getattr(d, "reservation_supported", False),
        "reservation_required": getattr(d, "reservation_required", False),
        "guestlist_supported": getattr(d, "guestlist_supported", False),
        "table_booking_supported": getattr(d, "table_booking_supported", False),
        "entry_fee": getattr(d, "entry_fee", None),
        "minimum_spend": getattr(d, "minimum_spend", None),
        "table_minimum_spend": getattr(d, "table_minimum_spend", None),
        "age_restriction_min": getattr(d, "age_restriction_min", None),
        "id_check_required": getattr(d, "id_check_required", False),
        "dress_code_required": getattr(d, "dress_code_required", False),
        "dress_code_description": getattr(d, "dress_code_description", None),
        "seating_capacity": getattr(d, "seating_capacity", None),
        "indoor_seating": getattr(d, "indoor_seating", False),
        "outdoor_seating": getattr(d, "outdoor_seating", False),
        "private_room_available": getattr(d, "private_room_available", False),
        "dance_floor": getattr(d, "dance_floor", False),
        "standing_area": getattr(d, "standing_area", False),
        "parking_available": getattr(d, "parking_available", False),
        "wifi_available": getattr(d, "wifi_available", False),
        "wheelchair_access": getattr(d, "wheelchair_access", False),
        "air_conditioned": getattr(d, "air_conditioned", False),
        "toilet_available": getattr(d, "toilet_available", False),
        "smoking_allowed": getattr(d, "smoking_allowed", False),
        "smoking_area_available": getattr(d, "smoking_area_available", False),
        "shisha_available": getattr(d, "shisha_available", False),
        "alcohol_served": getattr(d, "alcohol_served", True),
        "payment_methods": getattr(d, "payment_methods", None) or [],
        "happy_hour_supported": getattr(d, "happy_hour_supported", False),
        "happy_hour_notes": getattr(d, "happy_hour_notes", None),
        "best_time_to_visit": getattr(d, "best_time_to_visit", None),
        "best_days_to_visit": getattr(d, "best_days_to_visit", None) or [],
        "peak_hours": getattr(d, "peak_hours", None),
        "wait_time_peak_minutes": getattr(d, "wait_time_peak_minutes", None),
        "last_order_time": getattr(d, "last_order_time", None),
        "queue_expected": getattr(d, "queue_expected", False),
        "queue_peak_minutes": getattr(d, "queue_peak_minutes", None),
        "view_type": getattr(d, "view_type", None),
        "sunset_good": getattr(d, "sunset_good", False),
        "photo_spot": getattr(d, "photo_spot", False),
        "suitable_for": getattr(d, "suitable_for", None) or [],
        "dietary_options": getattr(d, "dietary_options", None),
    }
