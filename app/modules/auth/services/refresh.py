from typing import Dict, Any
from datetime import datetime, UTC, timedelta
from fastapi import HTTPException, status, Request
from app.core.security import verify_and_revoke_refresh_token, create_access_token, create_refresh_token, hash_token
from app.core.config import settings
from app.prisma import prisma
from app.shared.utils.responses.response import create_success_response, create_error_response
from app.modules.auth.schemas.auth import RefreshTokenRequest
import logging

logger = logging.getLogger(__name__)


class RefreshTokenService:
    """Service for handling refresh token operations"""

    @staticmethod
    async def refresh_access_token(
        refresh_token: str, 
        request: Request
    ) -> Dict[str, Any]:
        """Refresh access token using a valid refresh token"""
        try:
            user_id = await verify_and_revoke_refresh_token(refresh_token)
            user = await prisma.user.find_unique(where={"id": user_id})
            
            if not user:
                return create_error_response(
                    error_code="USER_NOT_FOUND",
                    message="User not found. Please login again."
                )
            
            if user.banned:
                return create_error_response(
                    error_code="ACCOUNT_BANNED",
                    message="Account is banned. Please contact support."
                )

            access_token = create_access_token(data={"sub": str(user.id)})
            new_refresh_token = create_refresh_token(data={"sub": str(user.id), "type": "refresh"})
            await RefreshTokenService._store_refresh_token(
                user_id, 
                new_refresh_token, 
                request
            )
            await prisma.user.update(
                where={"id": user.id},
                data={"updated_at": datetime.now(UTC)}
            )
            
            # Build user data from User model directly
            user_data = {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "nickname": user.nickname,
                "role": user.role or "STAFF",
                "is_active": not user.banned,
                "emailVerified": user.email_verified,
                "phoneNumber": user.phone_number,
                "phoneNumberVerified": user.phone_number_verified,
                "avatar_url": user.avatar_url,
                "language_pref": user.language_pref,
                "theme_pref": user.theme_pref,
                "createdAt": user.created_at.isoformat(),
                "updatedAt": user.updated_at.isoformat()
            }

            return create_success_response(
                data={
                    "access_token": access_token,
                    "refresh_token": new_refresh_token,
                    "token_type": "bearer",
                    "expires_in": settings.access_token_expire_minutes * 60,
                    "refresh_expires_in": settings.refresh_token_expire_days * 24 * 60 * 60,
                    "user": user_data
                },
                message="Token refreshed successfully"
            )

        except ValueError as e:
            error_message = str(e)
            if "expired" in error_message.lower():
                return create_error_response(
                    error_code="TOKEN_EXPIRED",
                    message="Refresh token has expired. Please login again."
                )
            elif "invalid" in error_message.lower():
                return create_error_response(
                    error_code="INVALID_TOKEN",
                    message="Invalid refresh token. Please login again."
                )
            else:
                return create_error_response(
                    error_code="TOKEN_VERIFICATION_FAILED",
                    message=f"Token verification failed: {error_message}"
                )
        except Exception as e:
            return create_error_response(
                error_code="REFRESH_FAILED",
                message=f"Failed to refresh token: {str(e)}"
            )

    @staticmethod
    async def _store_refresh_token(
        user_id: str, 
        refresh_token: str, 
        request: Request
    ) -> None:
        """Store refresh token in database with device tracking"""
        try:
            import jwt
            
            # Extract expiration time from the JWT token (same as login service)
            from app.core.security import ALGORITHM
            payload = jwt.decode(
                refresh_token, settings.jwt_secret, algorithms=[ALGORITHM])
            exp_timestamp = payload.get("exp")
            expire_time = datetime.fromtimestamp(exp_timestamp, UTC)
            
            token_hash = hash_token(refresh_token)
            user_agent = request.headers.get("user-agent", "")
            ip_address = request.client.host if request.client else None
            
            await prisma.refreshtoken.create(
                data={
                    "user_id": user_id,
                    "token_hash": token_hash,
                    "expires_at": expire_time,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "is_revoked": False
                }
            )
            
        except Exception as e:
            logger.warning("Failed to store refresh token: %s", e)


async def refresh_token_endpoint(
    refresh_data: RefreshTokenRequest, 
    request: Request
) -> Dict[str, Any]:
    """Endpoint handler for token refresh"""
    try:
        result = await RefreshTokenService.refresh_access_token(
            refresh_data.refresh_token,
            request
        )

        if not result.success:
            if hasattr(result, 'error'):
                error_code = result.error.get("code", "REFRESH_FAILED")
                error_message = result.error.get("message", "Failed to refresh token")
                
                status_code = status.HTTP_401_UNAUTHORIZED
                if error_code == "USER_NOT_FOUND":
                    status_code = status.HTTP_404_NOT_FOUND
                elif error_code == "ACCOUNT_BANNED":
                    status_code = status.HTTP_403_FORBIDDEN
                elif error_code in ["TOKEN_EXPIRED", "INVALID_TOKEN"]:
                    status_code = status.HTTP_401_UNAUTHORIZED
                elif error_code == "TOKEN_VERIFICATION_FAILED":
                    status_code = status.HTTP_400_BAD_REQUEST
                
                raise HTTPException(
                    status_code=status_code,
                    detail=error_message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Failed to refresh token"
                )
        
        return result

    except HTTPException:
        raise
    except Exception as e:
        error_message = str(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error refreshing token: {error_message}"
        )
