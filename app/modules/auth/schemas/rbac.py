from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from app.shared.schemas.base import BaseEntity
from enum import Enum

class BusinessType(str, Enum):
    TOURISM_BOARD = "TOURISM_BOARD"
    VENDOR = "VENDOR"
    ADMIN = "ADMIN"
    PARTNER = "PARTNER"

class BusinessCreate(BaseModel):
    """Schema for creating an business"""
    type: BusinessType
    name: str = Field(..., min_length=1, max_length=255)
    country_code: Optional[str] = Field(None, max_length=5)

class BusinessUpdate(BaseModel):
    """Schema for updating an business"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    country_code: Optional[str] = Field(None, max_length=5)

class BusinessResponse(BaseEntity):
    """Schema for business response"""
    type: BusinessType
    name: str
    country_code: Optional[str] = None

class RbacRoleCreate(BaseModel):
    """Schema for creating a role"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    permissions: List[str] = Field(..., min_items=1)
    business_type: Optional[BusinessType] = None

class RbacRoleUpdate(BaseModel):
    """Schema for updating a role"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    permissions: Optional[List[str]] = Field(None, min_items=1)
    business_type: Optional[BusinessType] = None

class RbacRoleResponse(BaseEntity):
    """Schema for role response"""
    name: str
    description: Optional[str] = None
    permissions: List[str]
    business_type: Optional[BusinessType] = None

class RbacUserRoleAssign(BaseModel):
    """Schema for assigning a role to a user"""
    user_id: UUID
    role_id: UUID
    business_id: UUID

class RbacUserRoleResponse(BaseEntity):
    """Schema for user role response"""
    user_id: UUID
    role_id: UUID
    business_id: UUID
    assigned_at: datetime
    user: Optional[dict] = None  # User details
    role: Optional[dict] = None  # Role details
    business: Optional[dict] = None  # Business details

class UserSessionResponse(BaseModel):
    """Schema for user session with permissions"""
    user: dict
    permissions: List[str]
    roles: List[dict]
    business: List[dict]

class PermissionCheck(BaseModel):
    """Schema for checking permissions"""
    permission: str
    business_id: Optional[UUID] = None
