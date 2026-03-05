"""Attraction API schemas aligned with Prisma Attraction model."""
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
    RESERVATION = "RESERVATION"
    HOUSE_RULES = "HOUSE_RULES"
    OTHER = "OTHER"


# ── Nested / related ───────────────────────────────────────────────────────

class GalleryImageIn(BaseModel):
    url: Optional[str] = None
    description: Optional[str] = None
    is_cover: bool = False
    url_file: Optional[Any] = None


class GalleryFileMetadataIn(BaseModel):
    is_cover: bool = False
    description: Optional[str] = None
    file: Optional[Any] = None


class TagIn(BaseModel):
    tag_type: str
    tag_value: str


class PolicyIn(BaseModel):
    policy_type: PolicyTypeEnum
    policy_text: str


class TranslationIn(BaseModel):
    name: Optional[str] = None
    short_description: Optional[str] = None


class WeeklyDay(BaseModel):
    open: Optional[str] = None
    close: Optional[str] = None
    is_closed: bool = False


class HoursIn(BaseModel):
    timezone: Optional[str] = None
    weekly_schedule: Dict[str, WeeklyDay]
    special_notes: Optional[List[str]] = None


class AttractionDetailsIn(BaseModel):
    attraction_type: List[str] = Field(default_factory=list)
    ownership_type: List[str] = Field(default_factory=list)
    entry_fee_adult: Optional[int] = None
    entry_fee_child: Optional[int] = None
    ticketing_type: str = ""
    recommended_visit_duration_minutes: Optional[int] = None
    best_visit_time: str = ""
    seasonality: str = ""
    weather_dependency: str = ""
    difficulty_level: str = ""
    walking_required: bool = False
    stairs_required: bool = False
    wheelchair_access: bool = False
    family_friendly: bool = False
    guide_available: bool = False
    photo_spot: bool = False
    swim_allowed: bool = False
    dress_code_required: bool = False
    dress_code_description: Optional[str] = None
    safety_notes: Optional[str] = None
    facilities: Optional[Dict[str, Any]] = None
    travel_time_from_city_center_minutes: Optional[int] = None
    combo_with: List[str] = Field(default_factory=list)
    dietary_options: Optional[Dict[str, Any]] = None
    reservation_supported: bool = False
    reservation_required: bool = False
    payment_methods: List[str] = Field(default_factory=list)
    alcohol_served: bool = False
    parking_available: bool = False
    wifi_available: bool = False
    noise_level: Optional[str] = None


# ── Main attraction payload ─────────────────────────────────────────────────

class AttractionCreate(BaseModel):
    """Payload to create an attraction."""
    id: Optional[str] = None
    category: str
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
    languages_supported: List[str] = Field(default_factory=list)
    cover_image_url: Optional[str] = None
    cover_image_file: Optional[Any] = None
    gallery_urls: List[GalleryImageIn] = Field(default_factory=list)
    gallery_files: Optional[List[GalleryFileMetadataIn]] = None
    rating_avg: Optional[float] = None
    rating_count: int = 0
    trust_score: Optional[int] = None
    quality_score: Optional[int] = None
    popularity_score: Optional[int] = None
    tags: List[Union[TagIn, str]] = Field(default_factory=list)
    hours: Optional[HoursIn] = None
    policies: List[PolicyIn] = Field(default_factory=list)
    translations: Optional[Dict[str, TranslationIn]] = None
    details: Optional[AttractionDetailsIn] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @model_validator(mode="before")
    @classmethod
    def opening_hours_alias(cls, data: Any) -> Any:
        if isinstance(data, dict) and "opening_hours" in data and "hours" not in data:
            data = {**data, "hours": data["opening_hours"]}
        return data

    @model_validator(mode="after")
    def normalize_tags(self) -> "AttractionCreate":
        normalized: List[TagIn] = []
        for t in self.tags or []:
            if isinstance(t, str):
                normalized.append(TagIn(tag_type="OTHER", tag_value=t))
            else:
                normalized.append(t)
        return self.model_copy(update={"tags": normalized})


class AttractionUpdate(BaseModel):
    """Partial update payload."""
    vendor_name: Optional[str] = None
    contact_phone: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    verification_status: Optional[VerificationStatusEnum] = None
    name: Optional[str] = None
    slug: Optional[str] = None
    status: Optional[ListingStatusEnum] = None
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
    cover_image_url: Optional[str] = None
    rating_avg: Optional[float] = None
    rating_count: Optional[int] = None
    trust_score: Optional[int] = None
    quality_score: Optional[int] = None
    popularity_score: Optional[int] = None
    tags: Optional[List[TagIn]] = None
    hours: Optional[HoursIn] = None
    policies: Optional[List[PolicyIn]] = None
    translations: Optional[Dict[str, TranslationIn]] = None
    details: Optional[AttractionDetailsIn] = None


class AttractionFilters(BaseModel):
    """Query filters for list endpoint."""
    province: Optional[str] = None
    district: Optional[str] = None
    status: Optional[ListingStatusEnum] = None
    category: Optional[str] = None
