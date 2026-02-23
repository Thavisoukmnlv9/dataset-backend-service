from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from datetime import UTC, date, datetime
from uuid import UUID
from decimal import Decimal


class ResponseModel(BaseModel):
    """Base response model for all API endpoints"""
    success: bool = True
    data: Optional[Any] = None
    message: str = "Operation successful"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    request_id: Optional[str] = None

    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }


class ErrorResponse(BaseModel):
    """Standard error response model"""
    success: bool = False
    error: Dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    request_id: Optional[str] = None


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints"""
    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort: Optional[str] = Field(default="created_at", description="Sort field")
    order: str = Field(default="desc", pattern="^(asc|desc)$",
                       description="Sort order")

    @property
    def skip(self) -> int:
        """Calculate skip value for database queries"""
        return (self.page - 1) * self.limit

    @property
    def offset(self) -> int:
        """Calculate offset value for pagination response"""
        return (self.page - 1) * self.limit


class PaginationResponse(BaseModel):
    """Pagination response model"""
    page: int
    limit: int
    total: int
    pages: int
    offset: int
    has_next: bool
    has_prev: bool


class BaseEntity(BaseModel):
    """Base entity model with common fields"""
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None


class Location(BaseModel):
    """Location model for attractions and services"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None


class MediaItem(BaseModel):
    """Media item model for images and videos"""
    url: str
    caption: Optional[str] = None
    type: str = Field(default="image", pattern="^(image|video)$")
    size: Optional[int] = None  # Size in bytes
    mime_type: Optional[str] = None
