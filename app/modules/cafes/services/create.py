"""Create cafe: Vendor (if inline) + Cafe + details, tags, hours, media, policies, translations, rag_sources. No Qdrant."""
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


async def _upload_gallery_files(files: List[UploadFile]) -> List[str]:
    urls: List[str] = []
    for f in files or []:
        if not f or not getattr(f, "filename", None):
            continue
        result = await storage_service.upload_file(f, "cafes/gallery")
        if result.success and result.data:
            path = _to_stored_path(result.data.get("object_name"))
            if path:
                urls.append(path)
    return urls


def _serialize_cafe(c: Any) -> Dict[str, Any]:
    """Turn Prisma cafe model into JSON-serializable dict."""
    if not c:
        return {}
    return {
        "id": c.id,
        "listing_id": getattr(c, "listing_id", None),
        "vendor_id": c.vendor_id,
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
        "gallery_urls": list(c.gallery_urls) if getattr(c, "gallery_urls", None) else [],
        "rating_avg": c.rating_avg,
        "rating_count": c.rating_count or 0,
        "review_summary_text": getattr(c, "review_summary_text", None),
        "trust_score": c.trust_score,
        "quality_score": c.quality_score,
        "popularity_score": c.popularity_score,
        "last_verified_at": c.last_verified_at.isoformat() if getattr(c, "last_verified_at", None) else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        "vendor": _serialize_vendor(c.vendor) if getattr(c, "vendor", None) else None,
        "tags": [{"tag_type": t.tag_type, "tag_value": t.tag_value} for t in (c.tags or [])],
        "hours": _serialize_hours(c.hours) if c.hours else None,
        "media": [_serialize_media(m) for m in (c.media or [])],
        "policies": [_serialize_policy(p) for p in (c.policies or [])],
        "translations": {t.language: {"name": t.name, "short_description": t.short_description, "long_description": getattr(t, "long_description", None)} for t in (c.translations or [])},
        "category_details": _serialize_details(c.details) if c.details else None,
        "rag_sources": [_serialize_rag_source(rs) for rs in (c.rag_sources or [])],
        "menu": _serialize_cafe_menu(c.menu) if getattr(c, "menu", None) else None,
    }


def _serialize_vendor(v: Any) -> Optional[Dict[str, Any]]:
    if not v:
        return None
    return {
        "id": v.id,
        "vendor_id": getattr(v, "vendor_id", None),
        "name": v.name,
        "vendor_type": v.vendor_type,
        "contact_phone": v.contact_phone,
        "whatsapp": v.whatsapp,
        "email": v.email,
        "languages_supported": v.languages_supported or [],
        "verification_status": v.verification_status,
        "rating_avg": v.rating_avg,
        "rating_count": v.rating_count or 0,
        "response_time_avg_minutes": getattr(v, "response_time_avg_minutes", None),
        "created_at": v.created_at.isoformat() if v.created_at else None,
        "updated_at": v.updated_at.isoformat() if v.updated_at else None,
    }


def _serialize_hours(h: Any) -> Optional[Dict[str, Any]]:
    if not h:
        return None
    return {
        "timezone": h.timezone,
        "weekly_schedule": h.weekly_schedule,
    }


def _serialize_media(m: Any) -> Dict[str, Any]:
    if not m:
        return {}
    return {
        "media_type": m.media_type,
        "url": path_to_upload_url(m.url),
        "caption": m.caption,
        "sort_order": m.sort_order,
        "source": m.source,
        "is_verified": getattr(m, "is_verified", False),
    }


def _serialize_policy(p: Any) -> Dict[str, Any]:
    if not p:
        return {}
    return {
        "policy_type": p.policy_type,
        "policy_text": p.policy_text,
        "structured_policy": getattr(p, "structured_policy", None),
    }


def _serialize_details(d: Any) -> Optional[Dict[str, Any]]:
    if not d:
        return None
    return {
        "cafe_type": d.cafe_type,
        "coffee_styles": d.coffee_styles or [],
        "tea_options": d.tea_options,
        "dessert_available": d.dessert_available,
        "avg_spend_per_person": d.avg_spend_per_person,
        "wifi_quality": d.wifi_quality,
        "power_outlets_available": d.power_outlets_available,
        "work_friendly": d.work_friendly,
        "quiet_level": d.quiet_level,
        "stay_duration_friendly": d.stay_duration_friendly,
        "air_conditioning": d.air_conditioning,
        "smoking_area": getattr(d, "smoking_area", None),
        "opening_early": d.opening_early,
        "late_open": d.late_open,
        "instagrammable_score": getattr(d, "instagrammable_score", None),
        "view_type": d.view_type,
    }


def _serialize_rag_chunk(ch: Any) -> Dict[str, Any]:
    if not ch:
        return {}
    return {
        "chunk_id": getattr(ch, "chunk_id", None),
        "chunk_type": ch.chunk_type,
        "chunk_text": ch.chunk_text,
    }


def _serialize_rag_source(rs: Any) -> Dict[str, Any]:
    if not rs:
        return {}
    return {
        "document_id": getattr(rs, "document_id", None),
        "source_type": rs.source_type,
        "language": rs.language,
        "chunks": [_serialize_rag_chunk(ch) for ch in (getattr(rs, "chunks", None) or [])],
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
    vendor_id: Optional[str] = data.vendor_id
    if data.vendor and not vendor_id:
        # Create vendor first
        v = data.vendor
        vendor = await prisma.vendor.create(
            data={
                "vendor_id": v.vendor_id,
                "name": v.name,
                "vendor_type": v.vendor_type.value,
                "contact_phone": v.contact_phone,
                "whatsapp": v.whatsapp,
                "email": v.email,
                "languages_supported": v.languages_supported or [],
                "verification_status": v.verification_status.value if v.verification_status else None,
                "rating_avg": v.rating_avg,
                "rating_count": v.rating_count or 0,
                "response_time_avg_minutes": v.response_time_avg_minutes,
            },
        )
        vendor_id = vendor.id
    if not vendor_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either vendor_id or vendor (inline vendor) is required",
        )

    cover_url = await _upload_cover_image(cover_image_file)
    if cover_url:
        data.cover_image_url = cover_url
    gallery_uploaded = await _upload_gallery_files(gallery_files or [])
    if gallery_uploaded:
        data.gallery_urls = list(data.gallery_urls) + gallery_uploaded

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
                "vendor_id": vendor_id,
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
                "gallery_urls": data.gallery_urls or [],
                "rating_avg": data.rating_avg,
                "rating_count": data.rating_count or 0,
                "review_summary_text": data.review_summary_text,
                "trust_score": data.trust_score,
                "quality_score": data.quality_score,
                "popularity_score": data.popularity_score,
                "last_verified_at": data.last_verified_at,
            }
            if data.tags:
                create_data["tags"] = {
                    "create": [{"tag_type": t.tag_type.value, "tag_value": t.tag_value} for t in data.tags]
                }
            if data.hours and getattr(data.hours, "weekly_schedule", None):
                create_data["hours"] = {
                    "create": {
                        "timezone": getattr(data.hours, "timezone", None),
                        "weekly_schedule": PrismaJson(_to_prisma_weekly_schedule(data.hours)),
                    }
                }
            if data.media:
                create_data["media"] = {
                    "create": [
                        {
                            "media_type": m.media_type,
                            "url": m.url,
                            "caption": m.caption,
                            "sort_order": m.sort_order,
                            "source": m.source,
                            "is_verified": m.is_verified,
                        }
                        for m in data.media
                    ]
                }
            if data.policies:
                create_data["policies"] = {
                    "create": [
                        {
                            "policy_type": p.policy_type.value,
                            "policy_text": p.policy_text,
                            "structured_policy": PrismaJson(p.structured_policy) if p.structured_policy is not None else None,
                        }
                        for p in data.policies
                    ]
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
            # RAG sources (create after cafe exists)
            if data.rag_sources:
                for rs in data.rag_sources:
                    rag = await tx.ragsource.create(
                        data={
                            "document_id": rs.document_id,
                            "cafe_id": cafe_id,
                            "source_type": rs.source_type,
                            "language": rs.language,
                        },
                    )
                    if rs.chunks:
                        await tx.ragchunk.create_many(
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

        created = await prisma.cafe.find_unique(
            where={"id": cafe_id},
            include={
                "vendor": True,
                "tags": True,
                "hours": True,
                "media": True,
                "policies": True,
                "translations": True,
                "details": True,
                "menu": {"include": {"sections": {"include": {"items": True}}}},
                "rag_sources": {"include": {"chunks": True}},
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
