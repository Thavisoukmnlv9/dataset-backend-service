from pydantic import BaseModel, Field, field_validator


class VerifySetupTokenRequest(BaseModel):
    """Schema for verify setup token request"""
    token: str = Field(..., description="Password setup token")
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class VerifySetupTokenResponse(BaseModel):
    """Schema for verify setup token response"""
    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    expires_at: str = Field(..., description="Token expiration time in ISO 8601 format")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "vendor@example.com",
                "expires_at": "2025-10-10T12:00:00Z"
            }
        }


class SetupPasswordRequest(BaseModel):
    """Schema for setup password request"""
    token: str = Field(..., description="Password setup token")
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
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "new_password": "SecurePass123!"
            }
        }


class SetupPasswordResponse(BaseModel):
    """Schema for setup password response"""
    message: str = Field(..., description="Response message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Password set successfully"
            }
        }

