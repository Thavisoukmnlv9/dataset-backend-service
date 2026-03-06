"""Create souvenir: Souvenir + details, tags, hours, gallery, policies, translations, products. No Qdrant."""
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

from app.modules.souvenirs.schemas.souvenir import (
    SouvenirCreate,
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
        return "souvenir-" + uuid.uuid4().hex[:8]
    s = re.sub(r"[^a-z0-9]+", "-", text.lower().strip()).strip("-")
    return s or "souvenir-" + uuid.uuid4().hex[:8]


async def _resolve_slug(tx: Any, slug: Optional[str], name: str) -> str:
    base = (slug or "").strip() or _slugify(name)
    candidate = base
    n = 0
    while True:
        existing = await tx.souvenir.find_unique(where={"slug": candidate})
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
        result = await storage_service.upload_file(file, "souvenirs")
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
    out: List[GalleryImageIn] = []
    for f in files or []:
        if not f or not getattr(f, "filename", None):
            continue
        result = await storage_service.upload_file(f, "souvenirs/gallery")
        if result.success and result.data:
            path = _to_stored_path(result.data.get("object_name"))
            if path:
                out.append(GalleryImageIn(url=path, description=None))
    return out


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
        "shop_type": getattr(d, "shop_type", None),
        "product_categories": getattr(d, "product_categories", None) or [],
        "specialties": getattr(d, "specialties", None) or [],
        "local_made_focus": getattr(d, "local_made_focus", False),
        "handmade_focus": getattr(d, "handmade_focus", False),
        "artisan_direct": getattr(d, "artisan_direct", False),
        "authenticity_claims": getattr(d, "authenticity_claims", None) or [],
        "authenticity_certificate_available": getattr(d, "authenticity_certificate_available", False),
        "artisan_story_available": getattr(d, "artisan_story_available", False),
        "cultural_significance_notes": getattr(d, "cultural_significance_notes", None),
        "origin_regions": getattr(d, "origin_regions", None) or [],
        "materials_used": getattr(d, "materials_used", None) or [],
        "customization_available": getattr(d, "customization_available", False),
        "customization_types": getattr(d, "customization_types", None) or [],
        "customization_notes": getattr(d, "customization_notes", None),
        "gift_wrapping": getattr(d, "gift_wrapping", False),
        "bulk_order_supported": getattr(d, "bulk_order_supported", False),
        "wholesale_available": getattr(d, "wholesale_available", False),
        "shipping_available": getattr(d, "shipping_available", False),
        "local_delivery_available": getattr(d, "local_delivery_available", False),
        "international_shipping": getattr(d, "international_shipping", False),
        "shipping_notes": getattr(d, "shipping_notes", None),
        "packaging_safe_for_travel": getattr(d, "packaging_safe_for_travel", False),
        "fragile_items_available": getattr(d, "fragile_items_available", False),
        "return_exchange_supported": getattr(d, "return_exchange_supported", False),
        "return_window_days": getattr(d, "return_window_days", None),
        "return_notes": getattr(d, "return_notes", None),
        "avg_spend_per_person": getattr(d, "avg_spend_per_person", None),
        "currency": getattr(d, "currency", None),
        "price_level_notes": getattr(d, "price_level_notes", None),
        "payment_methods": getattr(d, "payment_methods", None) or [],
        "staff_languages": getattr(d, "staff_languages", None) or [],
        "parking_available": getattr(d, "parking_available", False),
        "wifi_available": getattr(d, "wifi_available", False),
        "wheelchair_access": getattr(d, "wheelchair_access", False),
        "air_conditioned": getattr(d, "air_conditioned", False),
        "toilet_available": getattr(d, "toilet_available", False),
        "photo_spot": getattr(d, "photo_spot", False),
        "suitable_for": getattr(d, "suitable_for", None) or [],
        "best_for": getattr(d, "best_for", None) or [],
        "best_time_to_visit": getattr(d, "best_time_to_visit", None),
        "best_days_to_visit": getattr(d, "best_days_to_visit", None) or [],
        "peak_hours": getattr(d, "peak_hours", None),
        "wait_time_peak_minutes": getattr(d, "wait_time_peak_minutes", None),
        "queue_expected": getattr(d, "queue_expected", False),
        "queue_peak_minutes": getattr(d, "queue_peak_minutes", None),
    }


def _serialize_product(p: Any) -> Dict[str, Any]:
    if not p:
        return {}
    return {
        "id": p.id,
        "product_name": getattr(p, "product_name", None),
        "product_slug": getattr(p, "product_slug", None),
        "product_category": getattr(p, "product_category", None),
        "short_description": getattr(p, "short_description", None),
        "long_description": getattr(p, "long_description", None),
        "images": [
            {"url": path_to_upload_url(i.url), "description": getattr(i, "description", None), "is_cover": getattr(i, "is_cover", False)}
            for i in (getattr(p, "images", None) or [])
        ],
    }


def _serialize_souvenir(s: Any) -> Dict[str, Any]:
    if not s:
        return {}
    return {
        "id": s.id,
        "category": s.category,
        "name": s.name,
        "slug": s.slug,
        "status": s.status,
        "vendor_name": getattr(s, "vendor_name", None),
        "contact_phone": getattr(s, "contact_phone", None),
        "whatsapp": getattr(s, "whatsapp", None),
        "email": getattr(s, "email", None),
        "verification_status": getattr(s, "verification_status", None),
        "short_description": s.short_description,
        "long_description": s.long_description,
        "country": s.country,
        "province": s.province,
        "district": s.district,
        "village": s.village,
        "address_text": s.address_text,
        "latitude": s.latitude,
        "longitude": s.longitude,
        "price_band": s.price_band,
        "currency": s.currency,
        "min_price": s.min_price,
        "max_price": s.max_price,
        "booking_supported": s.booking_supported,
        "walk_in_supported": s.walk_in_supported,
        "languages_supported": s.languages_supported or [],
        "gallery": [{"url": path_to_upload_url(g.url), "description": getattr(g, "description", None), "is_cover": getattr(g, "is_cover", False)} for g in (s.gallery or [])],
        "rating_avg": s.rating_avg,
        "rating_count": s.rating_count or 0,
        "trust_score": s.trust_score,
        "quality_score": s.quality_score,
        "popularity_score": s.popularity_score,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        "tags": [{"tag_type": t.tag_type, "tag_value": t.tag_value} for t in (s.tags or [])],
        "hours": _serialize_hours(s.hours) if s.hours else None,
        "policies": [_serialize_policy(p) for p in (s.policies or [])],
        "translations": {t.language: {"name": t.name, "short_description": t.short_description, "long_description": getattr(t, "long_description", None)} for t in (s.translations or [])},
        "details": _serialize_details(s.details) if s.details else None,
        "products": [_serialize_product(p) for p in (s.products or [])],
    }


def _to_prisma_weekly_schedule(hours: Optional[Any]) -> Any:
    if not hours or not getattr(hours, "weekly_schedule", None):
        return {}
    return {k: v.model_dump() if hasattr(v, "model_dump") else v for k, v in hours.weekly_schedule.items()}


def _details_to_create_payload(cd: Any) -> Dict[str, Any]:
    if not cd:
        return {}
    return {
        "shop_type": cd.shop_type,
        "product_categories": cd.product_categories or [],
        "specialties": cd.specialties or [],
        "local_made_focus": cd.local_made_focus,
        "handmade_focus": cd.handmade_focus,
        "artisan_direct": cd.artisan_direct,
        "authenticity_claims": cd.authenticity_claims or [],
        "authenticity_certificate_available": cd.authenticity_certificate_available,
        "artisan_story_available": cd.artisan_story_available,
        "cultural_significance_notes": cd.cultural_significance_notes,
        "origin_regions": cd.origin_regions or [],
        "materials_used": cd.materials_used or [],
        "customization_available": cd.customization_available,
        "customization_types": cd.customization_types or [],
        "customization_notes": cd.customization_notes,
        "gift_wrapping": cd.gift_wrapping,
        "bulk_order_supported": cd.bulk_order_supported,
        "wholesale_available": cd.wholesale_available,
        "shipping_available": cd.shipping_available,
        "local_delivery_available": cd.local_delivery_available,
        "international_shipping": cd.international_shipping,
        "shipping_notes": cd.shipping_notes,
        "packaging_safe_for_travel": cd.packaging_safe_for_travel,
        "fragile_items_available": cd.fragile_items_available,
        "return_exchange_supported": cd.return_exchange_supported,
        "return_window_days": cd.return_window_days,
        "return_notes": cd.return_notes,
        "avg_spend_per_person": cd.avg_spend_per_person,
        "currency": cd.currency,
        "price_level_notes": cd.price_level_notes,
        "payment_methods": cd.payment_methods or [],
        "staff_languages": cd.staff_languages or [],
        "parking_available": cd.parking_available,
        "wifi_available": cd.wifi_available,
        "wheelchair_access": cd.wheelchair_access,
        "air_conditioned": cd.air_conditioned,
        "toilet_available": cd.toilet_available,
        "photo_spot": cd.photo_spot,
        "suitable_for": cd.suitable_for or [],
        "best_for": cd.best_for or [],
        "best_time_to_visit": cd.best_time_to_visit,
        "best_days_to_visit": cd.best_days_to_visit or [],
        "peak_hours": cd.peak_hours,
        "wait_time_peak_minutes": cd.wait_time_peak_minutes,
        "queue_expected": cd.queue_expected,
        "queue_peak_minutes": cd.queue_peak_minutes,
    }


async def create_souvenir(
    data: SouvenirCreate,
    cover_image_file: Optional[UploadFile] = None,
    gallery_files: Optional[List[UploadFile]] = None,
) -> Dict[str, Any]:
    cover_url = await _upload_cover_image(cover_image_file)
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
        if not cover_url:
            for g in data.gallery_urls:
                if getattr(g, "is_cover", False) and g.url:
                    cover_url = g.url
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
                "languages_supported": [c if isinstance(c, str) else str(c) for c in (data.languages_supported or [])],
                "cover_image_url": cover_url,
                "rating_avg": data.rating_avg,
                "rating_count": data.rating_count or 0,
                "trust_score": data.trust_score,
                "quality_score": data.quality_score,
                "popularity_score": data.popularity_score,
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
                    "create": [
                        {"tag_type": t.tag_type, "tag_value": t.tag_value or ""}
                        for t in data.tags
                    ]
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
                    "create": [
                        {"policy_type": p.policy_type.value if p.policy_type else None, "policy_text": p.policy_text or ""}
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
            if data.details:
                create_data["details"] = {"create": _details_to_create_payload(data.details)}
            if data.products:
                products_create = []
                for prod in data.products:
                    prod_payload: Dict[str, Any] = {
                        "product_name": prod.product_name,
                        "product_slug": prod.product_slug,
                        "product_category": prod.product_category,
                        "sku": prod.sku,
                        "short_description": prod.short_description,
                        "long_description": prod.long_description,
                        "material_type": prod.material_type,
                        "material_color": prod.material_color,
                        "material_size": prod.material_size,
                        "material_weight": prod.material_weight,
                        "material_shape": prod.material_shape,
                        "material_texture": prod.material_texture,
                        "origin_region": prod.origin_region,
                        "origin_country": prod.origin_country,
                        "is_handmade": prod.is_handmade,
                        "artisan_made": prod.artisan_made,
                        "authenticity_certificate": prod.authenticity_certificate,
                        "is_customizable": prod.is_customizable,
                        "customization_notes": prod.customization_notes,
                        "packaging_safe_for_travel": prod.packaging_safe_for_travel,
                        "fragile": prod.fragile,
                        "care_instructions": prod.care_instructions,
                    }
                    if prod.images:
                        prod_payload["images"] = {
                            "create": [{"url": i.url, "description": i.description, "is_cover": i.is_cover} for i in prod.images]
                        }
                    products_create.append(prod_payload)
                create_data["products"] = {"create": products_create}

            created_in_tx = await tx.souvenir.create(data=create_data)
            souvenir_id = created_in_tx.id

        created = await prisma.souvenir.find_unique(
            where={"id": souvenir_id},
            include={
                "tags": True,
                "hours": True,
                "gallery": True,
                "policies": True,
                "translations": True,
                "details": True,
                "products": {"include": {"images": True}},
            },
        )
        full_payload = _serialize_souvenir(created) if created else {"id": souvenir_id}
        return create_success_response(
            message="Souvenir created successfully",
            data={"souvenir": full_payload},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Create souvenir error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
