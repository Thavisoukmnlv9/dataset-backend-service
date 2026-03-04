"""Cafe API schemas aligned with Prisma Vendor + Cafe models."""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, model_validator


class ListingCategoryEnum(str, Enum):
    RESTAURANT = "RESTAURANT"
    CAFE = "CAFE"
    ATTRACTION = "ATTRACTION"
    VEHICLE_RENTAL = "VEHICLE_RENTAL"
    BAR = "BAR"
    SOUVENIR = "SOUVENIR"


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


class VendorTypeEnum(str, Enum):
    COMPANY = "COMPANY"
    INDIVIDUAL = "INDIVIDUAL"


class TagTypeEnum(str, Enum):
    VIBE = "VIBE"
    THEME = "THEME"
    OCCASION = "OCCASION"
    FEATURE = "FEATURE"
    CUISINE = "CUISINE"
    PURPOSE = "PURPOSE"
    OTHER = "OTHER"


class PolicyTypeEnum(str, Enum):
    CANCELLATION = "CANCELLATION"
    DEPOSIT = "DEPOSIT"
    RESERVATION = "RESERVATION"
    HOUSE_RULES = "HOUSE_RULES"
    OTHER = "OTHER"


class SpiceLevelEnum(str, Enum):
    MILD = "MILD"
    MEDIUM = "MEDIUM"
    HOT = "HOT"


# ── Vendor (inline create) ─────────────────────────────────────────────────

class VendorCreate(BaseModel):
    """Inline vendor payload when creating a cafe without existing vendor_id."""
    vendor_id: Optional[str] = None  # external id e.g. v_1101
    name: str
    vendor_type: VendorTypeEnum = VendorTypeEnum.COMPANY
    contact_phone: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    languages_supported: List[str] = Field(default_factory=list)
    verification_status: Optional[VerificationStatusEnum] = None
    rating_avg: Optional[float] = None
    rating_count: int = 0
    response_time_avg_minutes: Optional[int] = None


# ── Nested / related ───────────────────────────────────────────────────────

class TagIn(BaseModel):
    tag_type: TagTypeEnum
    tag_value: str


class WeeklyDay(BaseModel):
    open: Optional[str] = None
    close: Optional[str] = None
    is_closed: bool = False


class HoursIn(BaseModel):
    timezone: Optional[str] = None
    weekly_schedule: Dict[str, WeeklyDay]


class MediaIn(BaseModel):
    media_type: str = "image"
    url: str
    caption: Optional[str] = None
    sort_order: int = 0
    source: Optional[str] = None
    is_verified: bool = False


class PolicyIn(BaseModel):
    policy_type: PolicyTypeEnum
    policy_text: str
    structured_policy: Optional[Dict[str, Any]] = None


class TranslationIn(BaseModel):
    name: Optional[str] = None
    short_description: Optional[str] = None
    long_description: Optional[str] = None


class RagChunkIn(BaseModel):
    chunk_id: Optional[str] = None
    chunk_type: str
    chunk_text: str


class RagSourceIn(BaseModel):
    document_id: Optional[str] = None
    source_type: str = "listing_profile"
    language: str
    chunks: List[RagChunkIn] = Field(default_factory=list)


class CafeDetailsIn(BaseModel):
    """Cafe-specific category_details."""
    cafe_type: Optional[str] = None
    coffee_styles: List[str] = Field(default_factory=list)
    tea_options: bool = False
    dessert_available: bool = False
    avg_spend_per_person: Optional[int] = None
    wifi_quality: Optional[str] = None
    power_outlets_available: bool = False
    work_friendly: bool = False
    quiet_level: Optional[str] = None
    stay_duration_friendly: bool = False
    air_conditioning: bool = False
    smoking_area: Optional[bool] = None
    opening_early: bool = False
    late_open: bool = False
    instagrammable_score: Optional[int] = None
    view_type: Optional[str] = None


# ── Menu (same structure as restaurant) ─────────────────────────────────────

class MenuItemIn(BaseModel):
    item_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    price: Optional[int] = None
    currency: Optional[str] = None
    image_url: List[str] = Field(default_factory=list)
    image_description: Optional[str] = None
    image_file: Optional[Any] = None  # multipart placeholder
    dietary: Optional[Dict[str, Any]] = None
    spice_level: Optional[SpiceLevelEnum] = None
    allergens: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def image_url_to_list(cls, data: Any) -> Any:
        if isinstance(data, dict) and "image_url" in data:
            v = data["image_url"]
            if isinstance(v, str):
                data = {**data, "image_url": [v] if v.strip() else []}
            elif v is None:
                data = {**data, "image_url": []}
        return data


class MenuSectionIn(BaseModel):
    section_name: str
    source_type: Optional[str] = None
    items: List[MenuItemIn]


class MenuIn(BaseModel):
    source_type: str = "menu"
    source_version: Optional[str] = None
    source_url: Optional[str] = None
    source_file: Optional[Any] = None  # multipart: menu_source_file
    language: Optional[str] = None
    extracted_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    sections: List[MenuSectionIn] = Field(default_factory=list)


# ── Main cafe payload ──────────────────────────────────────────────────────

class CafeCreate(BaseModel):
    """Payload to create a cafe (vendor_id or inline vendor)."""
    # Vendor: either existing id or inline vendor to create
    vendor_id: Optional[str] = None
    vendor: Optional[VendorCreate] = None

    listing_id: Optional[str] = None  # external e.g. l_cafe_3001
    category: ListingCategoryEnum = ListingCategoryEnum.CAFE
    sub_category: Optional[str] = None
    name: str
    slug: Optional[str] = None
    status: ListingStatusEnum = ListingStatusEnum.ACTIVE
    short_description: Optional[str] = None
    long_description: Optional[str] = None

    country: str
    province: str
    district: str
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
    instant_confirmation: bool = False
    cancellation_policy_summary: Optional[str] = None

    child_friendly: bool = False
    pet_friendly: bool = False
    accessibility_features: Optional[Dict[str, Any]] = None

    languages_supported: List[str] = Field(default_factory=list)
    cover_image_url: Optional[str] = None
    gallery_urls: List[str] = Field(default_factory=list)

    rating_avg: Optional[float] = None
    rating_count: int = 0
    review_summary_text: Optional[str] = None
    trust_score: Optional[int] = None
    quality_score: Optional[int] = None
    popularity_score: Optional[int] = None
    last_verified_at: Optional[datetime] = None

    tags: List[Union[TagIn, dict]] = Field(default_factory=list)
    hours: Optional[HoursIn] = None
    media: List[MediaIn] = Field(default_factory=list)
    policies: List[PolicyIn] = Field(default_factory=list)
    translations: Optional[Dict[str, TranslationIn]] = None
    category_details: Optional[CafeDetailsIn] = None
    rag_sources: Optional[List[RagSourceIn]] = None
    menu: Optional[MenuIn] = None

    @model_validator(mode="after")
    def normalize_tags(self) -> "CafeCreate":
        normalized: List[TagIn] = []
        for t in self.tags or []:
            if isinstance(t, dict):
                normalized.append(TagIn(**t))
            elif isinstance(t, str):
                normalized.append(TagIn(tag_type=TagTypeEnum.OTHER, tag_value=t))
            else:
                normalized.append(t)
        return self.model_copy(update={"tags": normalized})


class CafeUpdate(BaseModel):
    """Partial update payload for cafe."""
    name: Optional[str] = None
    slug: Optional[str] = None
    status: Optional[ListingStatusEnum] = None
    sub_category: Optional[str] = None
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
    instant_confirmation: Optional[bool] = None
    cancellation_policy_summary: Optional[str] = None
    child_friendly: Optional[bool] = None
    pet_friendly: Optional[bool] = None
    accessibility_features: Optional[Dict[str, Any]] = None
    languages_supported: Optional[List[str]] = None
    cover_image_url: Optional[str] = None
    gallery_urls: Optional[List[str]] = None
    rating_avg: Optional[float] = None
    rating_count: Optional[int] = None
    review_summary_text: Optional[str] = None
    trust_score: Optional[int] = None
    quality_score: Optional[int] = None
    popularity_score: Optional[int] = None
    last_verified_at: Optional[datetime] = None
    tags: Optional[List[TagIn]] = None
    hours: Optional[HoursIn] = None
    media: Optional[List[MediaIn]] = None
    policies: Optional[List[PolicyIn]] = None
    translations: Optional[Dict[str, TranslationIn]] = None
    category_details: Optional[CafeDetailsIn] = None
    rag_sources: Optional[List[RagSourceIn]] = None
    menu: Optional[MenuIn] = None


class CafeFilters(BaseModel):
    """Query filters for list endpoint."""
    province: Optional[str] = None
    district: Optional[str] = None
    status: Optional[ListingStatusEnum] = None
    sub_category: Optional[str] = None
