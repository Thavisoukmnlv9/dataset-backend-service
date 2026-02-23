from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.shared.schemas.base import BaseEntity
from enum import Enum

class BusinessType(str, Enum):
    """Business type enum"""
    COMPANY = "company"
    GOVERNMENT = "GOVERNMENT"
    NGO = "NGO"
    EDUCATIONAL = "EDUCATIONAL"
    OTHER = "OTHER"

class UserCreate(BaseModel):
    """Schema for user registration"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    first_name: str = Field(..., min_length=1, max_length=100, description="User first name")
    last_name: str = Field(..., min_length=1, max_length=100, description="User last name")
    phone_number: Optional[str] = Field(None, max_length=20, description="Phone number")
    country_code: Optional[str] = Field(None, max_length=5, description="Country code (e.g., +856, +1)")
    language_pref: str = Field(default="en", max_length=10, description="Language preference")
    theme_pref: str = Field(default="dark", max_length=20, description="Theme preference")

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")

class UserUpdate(BaseModel):
    """Schema for user profile update"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    country_code: Optional[str] = Field(None, max_length=5)
    language_pref: Optional[str] = Field(None, max_length=10)
    theme_pref: Optional[str] = Field(None, max_length=20)
    avatar_url: Optional[str] = Field(None, max_length=500)

class UserResponse(BaseEntity):
    """Schema for user response"""
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    nickname: Optional[str] = None  # Computed field for backward compatibility
    phone_number: Optional[str] = None
    country_code: Optional[str] = None
    language_pref: str = "en"
    theme_pref: str = "dark"
    role: str = "VENDOR_STAFF"
    is_active: bool = True
    avatar_url: Optional[str] = None
    email_verified: bool = False
    phone_number_verified: bool = False
    last_login_at: Optional[datetime] = None
    login_count: int = 0

class TokenResponse(BaseModel):
    """Schema for authentication token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class SocialLoginRequest(BaseModel):
    """Schema for social login"""
    provider: str = Field(..., pattern="^(google|facebook|apple)$")
    access_token: str
    device_info: Optional[dict] = None

class EmailOTPVerificationRequest(BaseModel):
    """Schema for email OTP verification request"""
    email: EmailStr = Field(..., description="User email address")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")
    
    @field_validator('otp')
    @classmethod
    def validate_otp(cls, v: str) -> str:
        """Validate OTP format"""
        if not v.isdigit():
            raise ValueError('OTP must contain only digits')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "otp": "123456"
            }
        }

class ResendOTPRequest(BaseModel):
    """Schema for resend OTP request"""
    email: EmailStr = Field(..., description="User email address")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com"
            }
        }

class KYCSubmission(BaseModel):
    """Schema for KYC submission"""
    passport_number: str = Field(..., min_length=5, max_length=20)
    passport_expiry: str = Field(..., description="Passport expiry date (YYYY-MM-DD)")
    nationality: str = Field(..., max_length=3)
    date_of_birth: str = Field(..., description="Date of birth (YYYY-MM-DD)")

class KYCResponse(BaseEntity):
    """Schema for KYC response"""
    user_id: UUID
    status: str = Field(..., pattern="^(pending|approved|rejected)$")
    error_message: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    """Schema for token refresh"""
    refresh_token: str

class SessionResponse(BaseEntity):
    """Schema for session response"""
    user_id: str
    expires_at: datetime
    token: str
    session_fingerprint: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    impersonated_by: Optional[str] = None
    is_active: bool = True
    device_info: Optional[dict] = None
    last_activity: datetime
    is_trusted: bool = False
    security_level: str = "normal"

class RefreshTokenResponse(BaseEntity):
    """Schema for refresh token response"""
    user_id: str
    token_hash: str
    expires_at: datetime
    device_info: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_revoked: bool = False
    revoked_at: Optional[datetime] = None
    revoked_reason: Optional[str] = None
    replaced_by_id: Optional[str] = None

class ForgotPasswordRequest(BaseModel):
    """Schema for forgot password request"""
    email: EmailStr = Field(..., description="User email address")

class ResetPasswordRequest(BaseModel):
    """Schema for reset password request"""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password")

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class AdminChangePasswordRequest(BaseModel):
    """Schema for admin password change request"""
    user_id: str = Field(..., description="User ID whose password should be changed")
    new_password: str = Field(..., min_length=8, description="New password")

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "new_password": "NewSecurePass123!"
            }
        }

class BusinessCreate(BaseModel):
    """Schema for business creation"""
    name: str = Field(..., min_length=1, max_length=255, description="Business name")
    type: BusinessType = Field(..., description="Business type")
    description: Optional[str] = Field(None, description="Business description")
    country_code: Optional[str] = Field(None, max_length=3, description="Country code (ISO 3166-1 alpha-3)")
    website_url: Optional[str] = Field(None, max_length=500, description="Website URL")
    contact_email: Optional[EmailStr] = Field(None, description="Contact email")
    contact_phone: Optional[str] = Field(None, max_length=20, description="Contact phone")
    address: Optional[str] = Field(None, description="Business address")

class BusinessResponse(BaseEntity):
    """Schema for business response"""
    name: str
    type: BusinessType
    description: Optional[str] = None
    country_code: Optional[str] = None
    website_url: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    is_active: bool = True
