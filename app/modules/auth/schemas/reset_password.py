from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
from app.shared.schemas.base import BaseEntity


class ForgotPasswordRequest(BaseModel):
    """Schema for forgot password request"""
    email: EmailStr = Field(..., description="User email address")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com"
            }
        }


class ForgotPasswordResponse(BaseModel):
    """Schema for forgot password response"""
    message: str = Field(..., description="Response message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "If the email exists, a reset link has been sent"
            }
        }


class VerifyOTPRequest(BaseModel):
    """Schema for OTP verification request"""
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


class VerifyOTPResponse(BaseModel):
    """Schema for OTP verification response"""
    resetToken: str = Field(..., description="JWT reset token")
    expiresAt: str = Field(..., description="Token expiration time in ISO 8601 format")
    
    class Config:
        json_schema_extra = {
            "example": {
                "resetToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "expiresAt": "2025-10-10T12:00:00Z"
            }
        }


class ResetPasswordRequest(BaseModel):
    """Schema for reset password request"""
    new_password: str = Field(..., min_length=8, description="New password")
    token: Optional[str] = Field(None, description="Reset token (if not provided in Authorization header)")
    
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
                "new_password": "NewSecurePass123!"
            }
        }


class ResetPasswordResponse(BaseModel):
    """Schema for reset password response"""
    message: str = Field(..., description="Response message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Password reset successful"
            }
        }


class OTPData(BaseEntity):
    """Schema for OTP data in database"""
    user_id: Optional[str] = None
    email: str
    purpose: str
    otp_hash: str
    salt: str
    attempts: int = 0
    max_attempts: int = 5
    expires_at: datetime
    consumed_at: Optional[datetime] = None
    last_sent_at: Optional[datetime] = None


class ResetTokenData(BaseEntity):
    """Schema for reset token data in database"""
    jti: str
    user_id: str
    purpose: str
    expires_at: datetime
    used_at: Optional[datetime] = None


class RateLimitData(BaseEntity):
    """Schema for rate limit data"""
    identifier: str
    endpoint: str
    count: int = 1
    window_start: datetime
