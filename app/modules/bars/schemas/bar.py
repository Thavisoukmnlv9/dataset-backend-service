"""Bar API schemas aligned with Prisma Bar model."""
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
    tag_type: TagTypeEnum
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


class MenuItemIn(BaseModel):
    item_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    price: Optional[int] = None
    currency: Optional[str] = None
    image_url: List[str] = Field(default_factory=list)
    image_description: Optional[str] = None
    image_file: Optional[Any] = None
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
    source_file: Optional[Any] = None
    language: Optional[str] = None
    extracted_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    sections: List[MenuSectionIn] = Field(default_factory=list)


class CategoryDetailsIn(BaseModel):
    cuisine_types: List[str] = Field(default_factory=list)
    meal_types: List[str] = Field(default_factory=list)
    avg_spend_per_person: Optional[int] = None
    reservation_supported: bool = False
    reservation_required: bool = False
    seating_capacity: Optional[int] = None
    indoor_seating: bool = False
    outdoor_seating: bool = False
    takeaway_available: bool = False
    delivery_available: bool = False
    payment_methods: List[str] = Field(default_factory=list)
    signature_dishes: List[str] = Field(default_factory=list)
    alcohol_served: bool = False
    parking_available: bool = False
    wifi_available: bool = False
    noise_level: Optional[str] = None
    suitable_for: List[str] = Field(default_factory=list)
    best_time_to_visit: Optional[str] = None
    wait_time_peak_minutes: Optional[int] = None


# BarDetails: bar-specific details aligned with Prisma BarDetails model
class BarDetailsIn(BaseModel):
    bar_types: List[str] = Field(default_factory=list)
    vibe_tags: List[str] = Field(default_factory=list)
    music_types: List[str] = Field(default_factory=list)
    entertainment_types: List[str] = Field(default_factory=list)
    crowd_type: List[str] = Field(default_factory=list)
    avg_spend_per_person: Optional[int] = None
    currency: Optional[str] = None
    drink_categories: List[str] = Field(default_factory=list)
    signature_drinks: List[str] = Field(default_factory=list)
    food_available: bool = False
    food_style: List[str] = Field(default_factory=list)
    non_alcoholic_options: bool = False
    reservation_supported: bool = False
    reservation_required: bool = False
    guestlist_supported: bool = False
    table_booking_supported: bool = False
    entry_fee: Optional[int] = None
    minimum_spend: Optional[int] = None
    table_minimum_spend: Optional[int] = None
    age_restriction_min: Optional[int] = None
    id_check_required: bool = False
    dress_code_required: bool = False
    dress_code_description: Optional[str] = None
    seating_capacity: Optional[int] = None
    indoor_seating: bool = False
    outdoor_seating: bool = False
    private_room_available: bool = False
    dance_floor: bool = False
    standing_area: bool = False
    parking_available: bool = False
    wifi_available: bool = False
    wheelchair_access: bool = False
    air_conditioned: bool = False
    toilet_available: bool = False
    smoking_allowed: bool = False
    smoking_area_available: bool = False
    shisha_available: bool = False
    alcohol_served: bool = True
    payment_methods: List[str] = Field(default_factory=list)
    happy_hour_supported: bool = False
    happy_hour_notes: Optional[str] = None
    best_time_to_visit: Optional[str] = None
    best_days_to_visit: List[str] = Field(default_factory=list)
    peak_hours: Optional[str] = None
    wait_time_peak_minutes: Optional[int] = None
    last_order_time: Optional[str] = None
    queue_expected: bool = False
    queue_peak_minutes: Optional[int] = None
    view_type: Optional[str] = None
    sunset_good: bool = False
    photo_spot: bool = False
    suitable_for: List[str] = Field(default_factory=list)


# ── Main bar payload ───────────────────────────────────────────────────────

class BarCreate(BaseModel):
    """Payload to create a bar."""
    id: Optional[str] = None
    vendor_name: Optional[str] = None
    contact_phone: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    verification_status: Optional[VerificationStatusEnum] = None
    category: ListingCategoryEnum = ListingCategoryEnum.BAR
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
    menu: Optional[MenuIn] = None
    category_details: Optional[BarDetailsIn] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @model_validator(mode="before")
    @classmethod
    def opening_hours_alias(cls, data: Any) -> Any:
        if isinstance(data, dict) and "opening_hours" in data and "hours" not in data:
            data = {**data, "hours": data["opening_hours"]}
        return data

    @model_validator(mode="before")
    @classmethod
    def coerce_gallery_descriptions(cls, data: Any) -> Any:
        if isinstance(data, dict) and data.get("gallery_descriptions") == "":
            data = {**data, "gallery_descriptions": None}
        return data

    @model_validator(mode="after")
    def normalize_tags(self) -> "BarCreate":
        normalized: List[TagIn] = []
        for t in self.tags or []:
            if isinstance(t, str):
                normalized.append(TagIn(tag_type=TagTypeEnum.OTHER, tag_value=t))
            else:
                normalized.append(t)
        return self.model_copy(update={"tags": normalized})


class BarUpdate(BaseModel):
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
    menu: Optional[MenuIn] = None
    category_details: Optional[BarDetailsIn] = None


class BarFilters(BaseModel):
    """Query filters for list endpoint."""
    province: Optional[str] = None
    district: Optional[str] = None
    status: Optional[ListingStatusEnum] = None
    category: Optional[ListingCategoryEnum] = None
