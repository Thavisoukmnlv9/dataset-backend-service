from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class UserStatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    BANNED = "BANNED"
    PENDING = "PENDING"


class UserRoleEnum(str, Enum):
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"
    STAFF = "STAFF"


class UserBase(BaseModel):
    """Base schema for User"""
    email: EmailStr = Field(..., description="User email address")
    password: Optional[str] = Field(None, description="User password (hashed)")
    
    # Profile Info
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    nickname: Optional[str] = Field(None, description="Full name")
    country_code: Optional[str] = Field(None, description="Country code")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    
    # Account Settings
    language_pref: str = Field(default="en", description="Language preference")
    email_verified: bool = Field(default=False, description="Email verified status")
    email_verified_at: Optional[datetime] = Field(None, description="Email verification date")
    phone_number_verified: bool = Field(default=False, description="Phone number verified status")
    phone_number: Optional[str] = Field(None, max_length=20, description="Phone number")
    theme_pref: str = Field(default="dark", description="Theme preference")
    
    # Social Login
    google_id: Optional[str] = Field(None, description="Google ID")
    facebook_id: Optional[str] = Field(None, description="Facebook ID")
    apple_id: Optional[str] = Field(None, description="Apple ID")
    social_provider: Optional[str] = Field(None, description="Social provider")
    
    # Security & Activity
    scope: Optional[str] = Field(None, max_length=500, description="OAuth scope")
    id_token: Optional[str] = Field(None, description="ID token")
    access_token: Optional[str] = Field(None, description="Access token")
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    access_token_expires_at: Optional[datetime] = Field(None, description="Access token expiration")
    refresh_token_expires_at: Optional[datetime] = Field(None, description="Refresh token expiration")
    last_login_at: Optional[datetime] = Field(None, description="Last login date")
    failed_login_attempts: int = Field(default=0, description="Failed login attempts")
    locked_until: Optional[datetime] = Field(None, description="Account lock until")
    
    # User Status
    role: UserRoleEnum = Field(default=UserRoleEnum.STAFF, description="User role")
    banned: bool = Field(default=False, description="Whether user is banned")
    ban_reason: Optional[str] = Field(None, description="Reason for ban")
    ban_expires: Optional[datetime] = Field(None, description="Ban expiration date")
    is_anonymous: bool = Field(default=False, description="Whether user is anonymous")
    last_logout_at: Optional[datetime] = Field(None, description="Last logout date")
    login_count: int = Field(default=0, description="Login count")
    deleted_at: Optional[datetime] = Field(None, description="Soft delete date")
    is_active: bool = Field(default=True, description="User active status")


class UserCreateRequest(BaseModel):
    """Schema for creating a user request"""
    email: EmailStr = Field(..., description="User email address")
    password: Optional[str] = Field(None, description="User password")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    phone_number: Optional[str] = Field(None, max_length=20, description="Phone number")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    role: Optional[UserRoleEnum] = Field(None, description="User role")
    is_anonymous: bool = Field(default=False, description="Whether user is anonymous")


class UserCreate(UserBase):
    """Schema for creating a user"""
    pass


class UserUpdate(BaseModel):
    """Schema for updating a user"""
    email: Optional[EmailStr] = Field(None, description="User email address")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    nickname: Optional[str] = Field(None, description="Full name")
    country_code: Optional[str] = Field(None, description="Country code")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    language_pref: Optional[str] = Field(None, description="Language preference")
    phone_number: Optional[str] = Field(None, max_length=20, description="Phone number")
    theme_pref: Optional[str] = Field(None, description="Theme preference")
    role: Optional[UserRoleEnum] = Field(None, description="User role")
    banned: Optional[bool] = Field(None, description="Whether user is banned")
    ban_reason: Optional[str] = Field(None, description="Reason for ban")
    ban_expires: Optional[datetime] = Field(None, description="Ban expiration date")
    is_anonymous: Optional[bool] = Field(None, description="Whether user is anonymous")
    is_active: Optional[bool] = Field(None, description="User active status")


class UserBanUpdate(BaseModel):
    """Schema for banning/unbanning a user"""
    banned: bool = Field(..., description="Whether to ban or unban user")
    ban_reason: Optional[str] = Field(None, description="Reason for ban")
    ban_expires: Optional[datetime] = Field(None, description="Ban expiration date")


class UserResponse(UserBase):
    """Schema for user response"""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Schema for user list response"""
    users: List[UserResponse]
    total: int
    page: int
    limit: int
    total_pages: int


class UserFilters(BaseModel):
    """Schema for user filters"""
    email: Optional[str] = None
    phone_number: Optional[str] = None
    role: Optional[UserRoleEnum] = None
    banned: Optional[bool] = None
    is_anonymous: Optional[bool] = None
    email_verified: Optional[bool] = None
    phone_number_verified: Optional[bool] = None
    is_active: Optional[bool] = None
    created_from: Optional[datetime] = None
    created_to: Optional[datetime] = None
    last_login_from: Optional[datetime] = None
    last_login_to: Optional[datetime] = None
    search: Optional[str] = Field(None, description="Search in email, phone_number, first_name, last_name")


class UserStatsResponse(BaseModel):
    """Schema for user statistics response"""
    total_users: int
    active_users: int
    banned_users: int
    verified_users: int
    anonymous_users: int
    users_by_role: dict
    recent_registrations: int  # Last 30 days
    recent_logins: int  # Last 7 days


class UserRoleCreateData(BaseModel):
    """Schema for user role creation data"""
    role_id: str


class UserFormDataCreate(BaseModel):
    """Schema for user creation with FormData"""
    email: str
    password: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    avatar_url: Optional[str] = None
    role: Optional[UserRoleEnum] = None
    is_anonymous: bool = False
    email_verified: bool = False
    phone_number_verified: bool = False
    last_login_at: Optional[datetime] = None
    login_count: int = 0
    user_roles: Optional[List[UserRoleCreateData]] = None


class UserLookupItem(BaseModel):
    """Schema for user lookup item"""
    id: str
    name: str


class UserLookupQueryDTO(BaseModel):
    """Schema for user lookup query"""
    q: Optional[str] = Field(None, description="Search query")
    limit: int = Field(20, ge=1, le=100, description="Number of items to return")
    skip: int = Field(0, ge=0, description="Number of items to skip")
