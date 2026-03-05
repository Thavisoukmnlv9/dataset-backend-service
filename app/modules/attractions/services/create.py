import logging
import re
import uuid
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status, UploadFile

from app.prisma import prisma
from app.prisma.generated.fields import Json as PrismaJson
from app.shared.utils.responses.response import create_success_response
from app.shared.utils.upload_urls import path_to_upload_url
from app.shared.services.infrastructure.storage import storage_service

from app.modules.attractions.schemas.attraction import (
    AttractionCreate,
    GalleryImageIn,
)

logger = logging.getLogger(__name__)

UPLOADS_PREFIX = "/uploads"


def _to_stored_path(object_name: Optional[str]) -> Optional[str]:
    """Convert storage object_name to path stored in Prisma: /uploads/attractions/..."""
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
        return "attraction-" + uuid.uuid4().hex[:8]
    s = re.sub(r"[^a-z0-9]+", "-", text.lower().strip()).strip("-")
    return s or "attraction-" + uuid.uuid4().hex[:8]


async def _resolve_slug(tx: Any, slug: Optional[str], name: str) -> str:
    """Return slug to use; if slug is None/empty, generate from name and ensure unique."""
    base = (slug or "").strip() or _slugify(name)
    candidate = base
    n = 0
    while True:
        existing = await tx.attraction.find_unique(where={"slug": candidate})
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
        result = await storage_service.upload_file(file, "attractions")
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


async def _upload_gallery_files(files: List[UploadFile]) -> List[GalleryImageIn]:
    out: List[GalleryImageIn] = []
    for f in files or []:
        if not f or not f.filename:
            continue
        result = await storage_service.upload_file(f, "attractions/gallery")
        if result.success and result.data:
            url = _to_stored_path(result.data.get("object_name"))
            if url:
                out.append(GalleryImageIn(url=url, description=None))
    return out


def _to_prisma_languages(codes: List[Any]) -> List[str]:
    return [c.value if hasattr(c, "value") else str(c) for c in codes]


def _to_prisma_weekly_schedule(hours: Optional[Any]) -> Any:
    if not hours or not getattr(hours, "weekly_schedule", None):
        return {}
    return {k: v.model_dump() if hasattr(v, "model_dump") else v for k, v in hours.weekly_schedule.items()}


async def create_attraction(
    data: AttractionCreate,
    cover_image_file: Optional[UploadFile] = None,
    gallery_files: Optional[List[UploadFile]] = None,
) -> Dict[str, Any]:
    cover_url = await _upload_cover_image(cover_image_file)
    if cover_url:
        data.cover_image_url = cover_url

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

    try:
        async with prisma.tx() as tx:
            resolved_slug = await _resolve_slug(tx, data.slug, data.name)

            create_data: Dict[str, Any] = {
                "category": data.category,
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
                        {"tag_type": t.tag_type, "tag_value": t.tag_value}
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

            created_in_tx = await tx.attraction.create(data=create_data)
            attraction_id = created_in_tx.id

            if data.details:
                dd = data.details
                details_create = {
                    "attraction_id": attraction_id,
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
                created_details = await tx.attractiondetails.create(data=details_create)

        created = await prisma.attraction.find_unique(
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
        full_payload = _serialize_attraction(created) if created else {"id": attraction_id}

        return create_success_response(
            message="Attraction created successfully",
            data={"attraction": full_payload},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Create attraction error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


def _serialize_attraction(r: Any) -> Dict[str, Any]:
    """Turn Prisma attraction model into JSON-serializable dict."""
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
        "attractionDetailsId": (r.details.id if r.details else None),
        "gallery": [
            {"url": path_to_upload_url(g.url), "description": g.description, "is_cover": getattr(g, "is_cover", False)}
            for g in (r.gallery or [])
        ],
        "tags": [{"tag_type": t.tag_type, "tag_value": t.tag_value} for t in (r.tags or [])],
        "policies": [{"policy_type": p.policy_type, "policy_text": p.policy_text} for p in (r.policies or [])],
        "translations": {
            t.language: {"name": t.name, "short_description": t.short_description}
            for t in (r.translations or [])
        },
        "hours": (
            {
                "timezone": getattr(r.hours, "timezone", None),
                "weekly_schedule": r.hours.weekly_schedule,
                "special_notes": getattr(r.hours, "special_notes", None),
            }
            if r.hours
            else None
        ),
        "details": _serialize_details(r.details) if r.details else None,
    }


def _serialize_details(d: Any) -> Optional[Dict[str, Any]]:
    if not d:
        return None
    return {
        "id": getattr(d, "id", None),
        "attraction_type": getattr(d, "attraction_type", None) or [],
        "ownership_type": getattr(d, "ownership_type", None) or [],
        "entry_fee_adult": getattr(d, "entry_fee_adult", None),
        "entry_fee_child": getattr(d, "entry_fee_child", None),
        "ticketing_type": getattr(d, "ticketing_type", None),
        "recommended_visit_duration_minutes": getattr(d, "recommended_visit_duration_minutes", None),
        "best_visit_time": getattr(d, "best_visit_time", None),
        "seasonality": getattr(d, "seasonality", None),
        "weather_dependency": getattr(d, "weather_dependency", None),
        "difficulty_level": getattr(d, "difficulty_level", None),
        "walking_required": getattr(d, "walking_required", False),
        "stairs_required": getattr(d, "stairs_required", False),
        "wheelchair_access": getattr(d, "wheelchair_access", False),
        "family_friendly": getattr(d, "family_friendly", False),
        "guide_available": getattr(d, "guide_available", False),
        "photo_spot": getattr(d, "photo_spot", False),
        "swim_allowed": getattr(d, "swim_allowed", False),
        "dress_code_required": getattr(d, "dress_code_required", False),
        "dress_code_description": getattr(d, "dress_code_description", None),
        "safety_notes": getattr(d, "safety_notes", None),
        "facilities": getattr(d, "facilities", None),
        "travel_time_from_city_center_minutes": getattr(d, "travel_time_from_city_center_minutes", None),
        "combo_with": getattr(d, "combo_with", None) or [],
        "dietary_options": getattr(d, "dietary_options", None),
        "reservation_supported": getattr(d, "reservation_supported", False),
        "reservation_required": getattr(d, "reservation_required", False),
        "payment_methods": getattr(d, "payment_methods", None) or [],
        "alcohol_served": getattr(d, "alcohol_served", False),
        "parking_available": getattr(d, "parking_available", False),
        "wifi_available": getattr(d, "wifi_available", False),
        "noise_level": getattr(d, "noise_level", None),
    }
