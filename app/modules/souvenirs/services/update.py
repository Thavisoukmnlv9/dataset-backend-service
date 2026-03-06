"""Update souvenir: PostgreSQL only (no Qdrant)."""
import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status, UploadFile

from app.prisma import prisma
from app.prisma.generated.fields import Json as PrismaJson
from app.shared.services.infrastructure.storage import storage_service
from app.shared.utils.responses.response import create_success_response

from app.modules.souvenirs.schemas.souvenir import SouvenirUpdate
from app.modules.souvenirs.services.create import (
    _serialize_souvenir,
    _to_stored_path,
    _to_prisma_weekly_schedule,
    _details_to_create_payload,
)

logger = logging.getLogger(__name__)


async def update_souvenir(
    souvenir_id: str,
    data: SouvenirUpdate,
    cover_image_file: Optional[UploadFile] = None,
    gallery_files: Optional[List[UploadFile]] = None,
) -> Dict[str, Any]:
    """Update souvenir; upload files if provided."""
    try:
        existing = await prisma.souvenir.find_unique(
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
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Souvenir not found")

        cover_url_path: Optional[str] = None
        if cover_image_file and getattr(cover_image_file, "filename", None):
            result = await storage_service.upload_file(cover_image_file, "souvenirs")
            if result.success and result.data:
                path = _to_stored_path(result.data.get("object_name"))
                if path:
                    cover_url_path = path
        if gallery_files:
            from app.modules.souvenirs.services.create import _upload_gallery_files
            gallery_uploaded = await _upload_gallery_files(gallery_files)
            if gallery_uploaded:
                existing_gallery = [{"url": g.url, "description": getattr(g, "description", None), "is_cover": getattr(g, "is_cover", False)} for g in (existing.gallery or [])]
                data.gallery_urls = existing_gallery + gallery_uploaded

        update_payload: Dict[str, Any] = {}
        if data.name is not None:
            update_payload["name"] = data.name
        if data.slug is not None:
            slug_exists = await prisma.souvenir.find_first(where={"slug": data.slug, "id": {"not": souvenir_id}})
            if slug_exists:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")
            update_payload["slug"] = data.slug
        if data.category is not None:
            update_payload["category"] = data.category
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
            update_payload["languages_supported"] = [c if isinstance(c, str) else str(c) for c in data.languages_supported]
        if cover_url_path is not None:
            update_payload["cover_image_url"] = cover_url_path
        if data.gallery_urls is not None:
            await prisma.souvenirgalleryimage.delete_many(where={"souvenir_id": souvenir_id})
            if data.gallery_urls:
                await prisma.souvenirgalleryimage.create_many(
                    data=[
                        {
                            "souvenir_id": souvenir_id,
                            "url": g.get("url", "") if isinstance(g, dict) else (getattr(g, "url", None) or ""),
                            "description": g.get("description") if isinstance(g, dict) else getattr(g, "description", None),
                            "is_cover": g.get("is_cover", False) if isinstance(g, dict) else getattr(g, "is_cover", False),
                        }
                        for g in data.gallery_urls
                    ]
                )
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
            await prisma.souvenir.update(where={"id": souvenir_id}, data=update_payload)

        if data.tags is not None:
            await prisma.souvenirtag.delete_many(where={"souvenir_id": souvenir_id})
            if data.tags:
                await prisma.souvenirtag.create_many(
                    data=[{"souvenir_id": souvenir_id, "tag_type": t.tag_type, "tag_value": t.tag_value or ""} for t in data.tags]
                )
        if data.hours is not None and getattr(data.hours, "weekly_schedule", None):
            hours_payload: Dict[str, Any] = {"weekly_schedule": PrismaJson(_to_prisma_weekly_schedule(data.hours))}
            if getattr(data.hours, "timezone", None):
                hours_payload["timezone"] = data.hours.timezone
            if getattr(data.hours, "special_notes", None) is not None:
                hours_payload["special_notes"] = PrismaJson(data.hours.special_notes)
            if existing.hours:
                await prisma.souvenirhours.update(where={"id": existing.hours.id}, data=hours_payload)
            else:
                await prisma.souvenirhours.create(data={"souvenir_id": souvenir_id, **hours_payload})
        if data.policies is not None:
            await prisma.souvenirpolicy.delete_many(where={"souvenir_id": souvenir_id})
            if data.policies:
                await prisma.souvenirpolicy.create_many(
                    data=[{"souvenir_id": souvenir_id, "policy_type": p.policy_type.value if p.policy_type else None, "policy_text": p.policy_text or ""} for p in data.policies]
                )
        if data.translations is not None:
            await prisma.souvenirtranslation.delete_many(where={"souvenir_id": souvenir_id})
            for lang, tr in data.translations.items():
                lang_str = lang if isinstance(lang, str) else str(lang)
                t = tr.model_dump() if hasattr(tr, "model_dump") else tr
                await prisma.souvenirtranslation.create(
                    data={
                        "souvenir_id": souvenir_id,
                        "language": lang_str,
                        "name": t.get("name"),
                        "short_description": t.get("short_description"),
                        "long_description": t.get("long_description"),
                    }
                )
        if data.details is not None:
            cd = data.details
            details_payload = _details_to_create_payload(cd)
            if existing.details:
                await prisma.souvenirdetails.update(where={"id": existing.details.id}, data=details_payload)
            else:
                await prisma.souvenirdetails.create(data={"souvenir_id": souvenir_id, **details_payload})

        if data.products is not None:
            # Delete existing products (cascade deletes images)
            for p in existing.products or []:
                await prisma.souvenirproduct.delete(where={"id": p.id})
            if data.products:
                for prod in data.products:
                    prod_payload: Dict[str, Any] = {
                        "souvenir_id": souvenir_id,
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
                    created_product = await prisma.souvenirproduct.create(data=prod_payload)
                    if prod.images:
                        await prisma.souvenirproductimage.create_many(
                            data=[
                                {"souvenir_product_id": created_product.id, "url": i.url, "description": i.description, "is_cover": i.is_cover}
                                for i in prod.images
                            ]
                        )

        updated = await prisma.souvenir.find_unique(
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
        out = _serialize_souvenir(updated)
        return create_success_response(message="Souvenir updated successfully", data={"souvenir": out})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("update_souvenir error: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
