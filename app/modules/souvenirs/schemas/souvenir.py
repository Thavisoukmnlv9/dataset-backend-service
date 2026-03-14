"""Souvenir API schemas aligned with Prisma Souvenir model."""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, model_validator


class ListingStatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DRAFT = "DRAFT"
    ARCHIVED = "ARCHIVED"


class PriceBandEnum(str, Enum):
    BUDGET = "BUDGET"
    LOW = "LOW"
    MID = "MID"
    HIGH = "HIGH"
    PREMIUM = "PREMIUM"
    LUXURY = "LUXURY"


class VerificationStatusEnum(str, Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class PolicyTypeEnum(str, Enum):
    CANCELLATION = "CANCELLATION"
    DEPOSIT = "DEPOSIT"
    RETURN_EXCHANGE = "RETURN_EXCHANGE"
    HOUSE_RULES = "HOUSE_RULES"
    OTHER = "OTHER"


# ── Nested / related ───────────────────────────────────────────────────────

class TagIn(BaseModel):
    tag_value: Optional[str] = None


class WeeklyDay(BaseModel):
    open: Optional[str] = None
    close: Optional[str] = None
    is_closed: bool = False


class HoursIn(BaseModel):
    timezone: Optional[str] = None
    weekly_schedule: Dict[str, WeeklyDay] = Field(default_factory=dict)
    special_notes: Optional[List[Any]] = None


class GalleryImageIn(BaseModel):
    url: Optional[str] = None
    description: Optional[str] = None
    is_cover: bool = False
    url_file: Optional[Any] = None


class GalleryFileMetadataIn(BaseModel):
    is_cover: bool = False
    description: Optional[str] = None
    file: Optional[Any] = None


class PolicyIn(BaseModel):
    policy_type: Optional[PolicyTypeEnum] = None
    policy_text: Optional[str] = None


class TranslationIn(BaseModel):
    name: Optional[str] = None
    short_description: Optional[str] = None
    long_description: Optional[str] = None


# ── SouvenirDetails (shop-level details) ────────────────────────────────────

class SouvenirDetailsIn(BaseModel):
    shop_type: Optional[str] = None
    product_categories: List[str] = Field(default_factory=list)
    specialties: List[str] = Field(default_factory=list)
    local_made_focus: bool = False
    handmade_focus: bool = False
    artisan_direct: bool = False
    authenticity_claims: List[str] = Field(default_factory=list)
    authenticity_certificate_available: bool = False
    artisan_story_available: bool = False
    cultural_significance_notes: Optional[str] = None
    origin_regions: List[str] = Field(default_factory=list)
    materials_used: List[str] = Field(default_factory=list)
    customization_available: bool = False
    customization_types: List[str] = Field(default_factory=list)
    customization_notes: Optional[str] = None
    gift_wrapping: bool = False
    bulk_order_supported: bool = False
    wholesale_available: bool = False
    shipping_available: bool = False
    local_delivery_available: bool = False
    international_shipping: bool = False
    shipping_notes: Optional[str] = None
    packaging_safe_for_travel: bool = False
    fragile_items_available: bool = False
    return_exchange_supported: bool = False
    return_window_days: Optional[int] = None
    return_notes: Optional[str] = None
    avg_spend_per_person: Optional[int] = None
    currency: Optional[str] = None
    price_level_notes: Optional[str] = None
    payment_methods: List[str] = Field(default_factory=list)
    staff_languages: List[str] = Field(default_factory=list)
    parking_available: bool = False
    wifi_available: bool = False
    wheelchair_access: bool = False
    air_conditioned: bool = False
    toilet_available: bool = False
    photo_spot: bool = False
    suitable_for: List[str] = Field(default_factory=list)
    best_for: List[str] = Field(default_factory=list)
    best_time_to_visit: Optional[str] = None
    best_days_to_visit: List[str] = Field(default_factory=list)
    peak_hours: Optional[str] = None
    wait_time_peak_minutes: Optional[int] = None
    queue_expected: bool = False
    queue_peak_minutes: Optional[int] = None


# ── SouvenirProduct ─────────────────────────────────────────────────────────

class SouvenirProductImageIn(BaseModel):
    url: Optional[str] = None
    description: Optional[str] = None
    is_cover: bool = False


class SouvenirProductIn(BaseModel):
    product_name: Optional[str] = None
    product_slug: Optional[str] = None
    product_category: Optional[str] = None
    sku: Optional[str] = None
    short_description: Optional[str] = None
    long_description: Optional[str] = None
    material_type: Optional[str] = None
    material_color: Optional[str] = None
    material_size: Optional[str] = None
    material_weight: Optional[str] = None
    material_shape: Optional[str] = None
    material_texture: Optional[str] = None
    origin_region: Optional[str] = None
    origin_country: Optional[str] = None
    is_handmade: bool = False
    artisan_made: bool = False
    authenticity_certificate: bool = False
    is_customizable: bool = False
    customization_notes: Optional[str] = None
    packaging_safe_for_travel: bool = False
    fragile: bool = False
    care_instructions: Optional[str] = None
    images: List[SouvenirProductImageIn] = Field(default_factory=list)


# ── Main souvenir payload ───────────────────────────────────────────────────

class SouvenirCreate(BaseModel):
    category: Optional[str] = None
    name: str
    slug: Optional[str] = None
    status: ListingStatusEnum = ListingStatusEnum.ACTIVE
    vendor_name: Optional[str] = None
    contact_phone: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    verification_status: Optional[VerificationStatusEnum] = None
    short_description: Optional[str] = None
    long_description: Optional[str] = None
    country: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None
    village: Optional[str] = None
    address_text: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    price_band: Optional[PriceBandEnum] = None
    currency: Optional[str] = None
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    booking_supported: bool = False
    walk_in_supported: bool = True
    languages_supported: List[str] = Field(default_factory=list)
    cover_image_file: Optional[Any] = None
    gallery_urls: List[GalleryImageIn] = Field(default_factory=list)
    gallery_files: Optional[List[GalleryFileMetadataIn]] = None
    rating_avg: Optional[float] = None
    rating_count: int = 0
    trust_score: Optional[int] = None
    quality_score: Optional[int] = None
    popularity_score: Optional[int] = None
    tags: List[Union[TagIn, dict, str]] = Field(default_factory=list)
    hours: Optional[HoursIn] = None
    policies: List[PolicyIn] = Field(default_factory=list)
    translations: Optional[Dict[str, TranslationIn]] = None
    details: Optional[SouvenirDetailsIn] = None
    products: List[SouvenirProductIn] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def flatten_vendor(cls, data: Any) -> Any:
        if not isinstance(data, dict) or "vendor" not in data:
            return data
        v = data.get("vendor")
        if not isinstance(v, dict):
            return data
        out = {**data}
        for key in ("vendor_name", "contact_phone", "whatsapp", "email", "verification_status", "languages_supported"):
            if key in v and out.get(key) is None:
                out[key] = v[key]
        return out

    @model_validator(mode="after")
    def normalize_tags(self) -> "SouvenirCreate":
        normalized: List[TagIn] = []
        for t in self.tags or []:
            if isinstance(t, dict):
                val = t.get("tag_value") if isinstance(t.get("tag_value"), str) else (str(t) if t else "")
                normalized.append(TagIn(tag_value=val or ""))
            elif isinstance(t, TagIn):
                normalized.append(t)
            else:
                normalized.append(TagIn(tag_value=str(t)))
        return self.model_copy(update={"tags": normalized})


class SouvenirUpdate(BaseModel):
    category: Optional[str] = None
    name: Optional[str] = None
    slug: Optional[str] = None
    status: Optional[ListingStatusEnum] = None
    vendor_name: Optional[str] = None
    contact_phone: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    verification_status: Optional[VerificationStatusEnum] = None
    short_description: Optional[str] = None
    long_description: Optional[str] = None
    country: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None
    village: Optional[str] = None
    address_text: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    price_band: Optional[PriceBandEnum] = None
    currency: Optional[str] = None
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    booking_supported: Optional[bool] = None
    walk_in_supported: Optional[bool] = None
    languages_supported: Optional[List[str]] = None
    gallery_urls: Optional[List[GalleryImageIn]] = None
    rating_avg: Optional[float] = None
    rating_count: Optional[int] = None
    trust_score: Optional[int] = None
    quality_score: Optional[int] = None
    popularity_score: Optional[int] = None
    tags: Optional[List[TagIn]] = None
    hours: Optional[HoursIn] = None
    policies: Optional[List[PolicyIn]] = None
    translations: Optional[Dict[str, TranslationIn]] = None
    details: Optional[SouvenirDetailsIn] = None
    products: Optional[List[SouvenirProductIn]] = None


class SouvenirCreateDraft(BaseModel):
    """Minimal payload to create a souvenir: name, location, country, contact."""
    souvenir_name: str = Field(..., description="Name of the souvenir shop")
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    country: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None
    village: Optional[str] = None
    contact_phone: Optional[str] = None


class SouvenirFilters(BaseModel):
    province: Optional[str] = None
    district: Optional[str] = None
    status: Optional[ListingStatusEnum] = None
    category: Optional[str] = None
