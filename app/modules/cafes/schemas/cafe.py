"""Cafe API schemas aligned with Prisma Cafe model."""
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


# ── Nested / related ───────────────────────────────────────────────────────

class TagIn(BaseModel):
    tag_value: str


class WeeklyDay(BaseModel):
    open: Optional[str] = None
    close: Optional[str] = None
    is_closed: bool = False


class HoursIn(BaseModel):
    timezone: Optional[str] = None
    weekly_schedule: Dict[str, WeeklyDay]
    special_notes: Optional[List[str]] = None  # like RestaurantHours


class GalleryImageIn(BaseModel):
    """Single gallery image (same as Restaurant)."""
    url: Optional[str] = None
    description: Optional[str] = None
    is_cover: bool = False
    url_file: Optional[Any] = None  # multipart placeholder; send file as gallery_0, gallery_1, ...


class GalleryFileMetadataIn(BaseModel):
    """Metadata for a gallery file upload (is_cover, description). The file is sent as gallery_files[i].file."""
    is_cover: bool = False
    description: Optional[str] = None
    file: Optional[Any] = None


class PolicyIn(BaseModel):
    policy_type: PolicyTypeEnum
    policy_text: str


class TranslationIn(BaseModel):
    name: Optional[str] = None
    short_description: Optional[str] = None
    long_description: Optional[str] = None


class CafeDetailsIn(BaseModel):
    """Cafe category_details aligned with Prisma CafeDetails model."""
    cafe_styles: List[str] = Field(default_factory=list)
    food_styles: List[str] = Field(default_factory=list)
    vibe_tags: List[str] = Field(default_factory=list)
    suitable_for: List[str] = Field(default_factory=list)

    avg_spend_per_person: Optional[int] = None
    currency: Optional[str] = None

    coffee_styles: List[str] = Field(default_factory=list)
    tea_options: List[str] = Field(default_factory=list)
    bean_types: List[str] = Field(default_factory=list)
    brew_methods: List[str] = Field(default_factory=list)
    specialty_coffee: bool = False
    non_coffee_options: bool = False

    signature_items: List[str] = Field(default_factory=list)
    signature_drinks: List[str] = Field(default_factory=list)
    dessert_available: bool = False
    pastry_available: bool = False
    dietary_options: Optional[Dict[str, Any]] = None

    reservation_supported: bool = False
    reservation_required: bool = False

    seating_capacity: Optional[int] = None
    indoor_seating: bool = False
    outdoor_seating: bool = False
    takeaway_available: bool = False
    delivery_available: bool = False

    laptop_friendly: bool = False
    good_for_work: bool = False
    good_for_study: bool = False
    meeting_friendly: bool = False
    power_outlets_available: bool = False
    power_outlet_count: Optional[int] = None
    wifi_available: bool = False
    wifi_speed_level: Optional[str] = None

    parking_available: bool = False
    restroom_available: bool = False
    air_conditioned: bool = False
    wheelchair_access: bool = False
    smoking_allowed: bool = False
    smoking_area_available: bool = False

    alcohol_served: bool = False
    payment_methods: List[str] = Field(default_factory=list)

    noise_level: Optional[str] = None
    crowd_level: Optional[str] = None
    best_time_to_visit: Optional[str] = None
    best_days_to_visit: List[str] = Field(default_factory=list)
    peak_hours: Optional[str] = None
    wait_time_peak_minutes: Optional[int] = None

    view_type: Optional[str] = None
    photo_spot: bool = False
    instagrammable: bool = False
    natural_light_good: bool = False
    sunrise_good: bool = False
    sunset_good: bool = False


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
    """Payload to create a cafe (inline vendor fields: vendor_name, contact_phone, etc.)."""
    vendor_name: Optional[str] = None
    contact_phone: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    verification_status: Optional[VerificationStatusEnum] = None

    listing_id: Optional[str] = None
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

    languages_supported: List[str] = Field(default_factory=list)
    cover_image_url: Optional[str] = None
    cover_image_file: Optional[Any] = None
    gallery_urls: List[GalleryImageIn] = Field(default_factory=list)
    gallery_files: Optional[List[GalleryFileMetadataIn]] = None

    rating_avg: Optional[float] = None
    rating_count: int = 0
    review_summary_text: Optional[str] = None
    trust_score: Optional[int] = None
    quality_score: Optional[int] = None
    popularity_score: Optional[int] = None
    last_verified_at: Optional[datetime] = None

    tags: List[Union[TagIn, dict, str]] = Field(default_factory=list)
    hours: Optional[HoursIn] = None
    policies: List[PolicyIn] = Field(default_factory=list)
    translations: Optional[Dict[str, TranslationIn]] = None
    category_details: Optional[CafeDetailsIn] = None
    menu: Optional[MenuIn] = None

    @model_validator(mode="before")
    @classmethod
    def flatten_vendor(cls, data: Any) -> Any:
        """Accept vendor: { vendor_name, contact_phone, ... } from form and flatten to top-level."""
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

    @model_validator(mode="before")
    @classmethod
    def opening_hours_alias(cls, data: Any) -> Any:
        """Same as Restaurant: accept opening_hours from form and map to hours."""
        if isinstance(data, dict) and "opening_hours" in data and "hours" not in data:
            data = {**data, "hours": data["opening_hours"]}
        return data

    @model_validator(mode="after")
    def normalize_tags(self) -> "CafeCreate":
        normalized: List[TagIn] = []
        for t in self.tags or []:
            if isinstance(t, dict):
                val = t.get("tag_value") if isinstance(t.get("tag_value"), str) else (str(t) if t else "")
                normalized.append(TagIn(tag_value=val or ""))
            elif isinstance(t, str):
                normalized.append(TagIn(tag_value=t))
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
    vendor_name: Optional[str] = None
    contact_phone: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    verification_status: Optional[VerificationStatusEnum] = None
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
    languages_supported: Optional[List[str]] = None
    cover_image_url: Optional[str] = None
    gallery_urls: Optional[List[GalleryImageIn]] = None
    rating_avg: Optional[float] = None
    rating_count: Optional[int] = None
    review_summary_text: Optional[str] = None
    trust_score: Optional[int] = None
    quality_score: Optional[int] = None
    popularity_score: Optional[int] = None
    last_verified_at: Optional[datetime] = None
    tags: Optional[List[TagIn]] = None
    hours: Optional[HoursIn] = None
    policies: Optional[List[PolicyIn]] = None
    translations: Optional[Dict[str, TranslationIn]] = None
    category_details: Optional[CafeDetailsIn] = None
    menu: Optional[MenuIn] = None


class CafeCreateDraft(BaseModel):
    """Minimal payload to create a cafe: name, location, country, contact."""
    cafe_name: str = Field(..., description="Name of the cafe")
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    country: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None
    village: Optional[str] = None
    contact_phone: Optional[str] = None


class CafeFilters(BaseModel):
    """Query filters for list endpoint (same pattern as RestaurantFilters)."""
    province: Optional[str] = None
    district: Optional[str] = None
    status: Optional[ListingStatusEnum] = None
    category: Optional[ListingCategoryEnum] = None
    sub_category: Optional[str] = None
