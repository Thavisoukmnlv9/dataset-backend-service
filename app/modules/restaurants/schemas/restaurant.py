"""Restaurant API schemas aligned with Prisma model and restaurant.json."""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ListingCategoryEnum(str, Enum):
    restaurant = "restaurant"
    cafe = "cafe"
    attraction = "attraction"
    vehicle_rental = "vehicle_rental"
    bar = "bar"
    souvenir = "souvenir"


class ListingStatusEnum(str, Enum):
    active = "active"
    inactive = "inactive"
    draft = "draft"
    archived = "archived"


class PriceBandEnum(str, Enum):
    budget = "budget"
    mid = "mid"
    premium = "premium"
    luxury = "luxury"


class TagTypeEnum(str, Enum):
    vibe = "vibe"
    theme = "theme"
    occasion = "occasion"
    feature = "feature"
    cuisine = "cuisine"
    other = "other"


class PolicyTypeEnum(str, Enum):
    cancellation = "cancellation"
    deposit = "deposit"
    reservation = "reservation"
    other = "other"


class LanguageCodeEnum(str, Enum):
    lo = "lo"
    en = "en"
    th = "th"


class SpiceLevelEnum(str, Enum):
    mild = "mild"
    medium = "medium"
    hot = "hot"


# ── Nested / related ───────────────────────────────────────────────────────

class GalleryImageIn(BaseModel):
    url: Optional[str] = None
    description: Optional[str] = None
    url_file: Optional[Any] = None  # multipart placeholder; send file as gallery_0, gallery_1, ...


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
    weekly_schedule: Dict[str, WeeklyDay]


class MenuItemIn(BaseModel):
    item_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    price: Optional[int] = None
    currency: Optional[str] = None
    image_url: Optional[str] = None
    image_description: Optional[str] = None
    image_file: Optional[Any] = None  # multipart placeholder (per-item image; use image_url or future form field)
    dietary: Optional[Dict[str, Any]] = None
    spice_level: Optional[SpiceLevelEnum] = None
    allergens: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class MenuSectionIn(BaseModel):
    section_name: str
    items: List[MenuItemIn]


class MenuIn(BaseModel):
    source_type: str = "menu"
    source_version: Optional[str] = None
    source_url: Optional[str] = None
    source_file: Optional[Any] = None  # multipart placeholder; send file as menu_source_file form field
    language: Optional[LanguageCodeEnum] = None
    extracted_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    sections: List[MenuSectionIn] = Field(default_factory=list)


class CategoryDetailsIn(BaseModel):
    cuisine_types: List[str] = Field(default_factory=list)
    meal_types: List[str] = Field(default_factory=list)
    avg_spend_per_person: Optional[int] = None
    dietary_options: Optional[Dict[str, Any]] = None
    reservation_supported: bool = False
    reservation_required: bool = False
    seating_capacity: Optional[int] = None
    indoor_seating: bool = False
    outdoor_seating: bool = False
    takeaway_available: bool = False
    delivery_available: bool = False
    payment_methods: List[str] = Field(default_factory=list)
    signature_dishes: List[str] = Field(default_factory=list)


# ── Main restaurant payload (snake_case for JSON upload) ───────────────────

class RestaurantCreate(BaseModel):
    """Payload to create a restaurant (e.g. from restaurant.json)."""
    id: Optional[str] = None  # If omitted, server can generate
    category: ListingCategoryEnum = ListingCategoryEnum.restaurant
    name: str
    slug: str
    status: ListingStatusEnum = ListingStatusEnum.active
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
    languages_supported: List[LanguageCodeEnum] = Field(default_factory=list)
    cover_image_url: Optional[str] = None
    cover_image_file: Optional[Any] = None
    gallery_urls: List[GalleryImageIn] = Field(default_factory=list)
    rating_avg: Optional[float] = None
    rating_count: int = 0
    trust_score: Optional[int] = None
    quality_score: Optional[int] = None
    popularity_score: Optional[int] = None
    tags: List[TagIn] = Field(default_factory=list)
    hours: Optional[HoursIn] = None
    policies: List[PolicyIn] = Field(default_factory=list)
    translations: Optional[Dict[str, TranslationIn]] = None
    menu: Optional[MenuIn] = None
    category_details: Optional[CategoryDetailsIn] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class RestaurantUpdate(BaseModel):
    """Partial update payload."""
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
    languages_supported: Optional[List[LanguageCodeEnum]] = None
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
    category_details: Optional[CategoryDetailsIn] = None

class RestaurantFilters(BaseModel):
    """Query filters for list endpoint."""
    province: Optional[str] = None
    district: Optional[str] = None
    status: Optional[ListingStatusEnum] = None
    category: Optional[ListingCategoryEnum] = None
