from typing import Dict, Any
from datetime import datetime, UTC, timedelta
from fastapi import HTTPException, status, Request
from app.core.security import verify_and_revoke_refresh_token, create_access_token, create_refresh_token, hash_token
from app.core.config import settings
from app.prisma import prisma
from app.shared.utils.responses.response import create_success_response, create_error_response
from app.modules.auth.schemas.auth import RefreshTokenRequest
import json


class VendorRefreshTokenService:
    """Service for handling vendor refresh token operations"""

    @staticmethod
    async def refresh_access_token(
        refresh_token: str, 
        request: Request
    ) -> Dict[str, Any]:
        """Refresh access token using a valid refresh token for vendor users"""
        try:
            user_id = await verify_and_revoke_refresh_token(refresh_token)
            user = await prisma.user.find_unique(
                where={"id": user_id},
                include={
                    "UserVendor": {
                        "include": {
                            "vendor": True
                        }
                    }
                }
            )
            
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

            # Check if user has a UserVendor relationship
            if not user.UserVendor or len(user.UserVendor) == 0:
                return create_error_response(
                    error_code="NOT_A_VENDOR",
                    message="User is not associated with any vendor"
                )

            # Get the first active UserVendor
            user_vendor = user.UserVendor[0]
            vendor = user_vendor.vendor
            
            # Check if vendor is approved and active
            # registration_status can be: PENDING, APPROVED, REJECTED
            # account_status can be: ACTIVE, SUSPENDED
            registration_status = vendor.registration_status.value if hasattr(vendor.registration_status, 'value') else str(vendor.registration_status)
            account_status = vendor.account_status.value if hasattr(vendor.account_status, 'value') else str(vendor.account_status)
            
            if registration_status != "APPROVED" or account_status != "ACTIVE":
                return create_error_response(
                    error_code="VENDOR_NOT_APPROVED",
                    message="Vendor account is not approved or is inactive"
                )

            # Create new tokens
            access_token = create_access_token(data={"sub": str(user.id)})
            new_refresh_token = create_refresh_token(data={"sub": str(user.id), "type": "refresh"})
            
            # Store new refresh token
            await VendorRefreshTokenService._store_refresh_token(
                user_id, 
                new_refresh_token, 
                request
            )
            
            # Update user
            await prisma.user.update(
                where={"id": user.id},
                data={"updated_at": datetime.now(UTC)}
            )
            
            # Get active session
            active_session = await prisma.session.find_first(
                where={
                    "user_id": user_id,
                    "is_active": True,
                    "expires_at": {"gt": datetime.now(UTC)}
                }
            )
            
            # Build user data
            user_data = {
                "id": user.id,
                "first_name": user.first_name or "",
                "last_name": user.last_name or "",
                "nickname": user.nickname,
                "email": user.email,
                "emailVerified": user.email_verified,
                "phoneNumber": user.phone_number,
                "phoneNumberVerified": user.phone_number_verified,
                "avatar_url": user.avatar_url,
                "language_pref": user.language_pref,
                "theme_pref": user.theme_pref,
                "role": user.role or "tourist",
                "banned": user.banned,
                "banReason": user.ban_reason,
                "banExpires": user.ban_expires.isoformat() if user.ban_expires else None,
                "isAnonymous": user.is_anonymous,
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
                "login_count": user.login_count,
                "createdAt": user.created_at.isoformat(),
                "updatedAt": user.updated_at.isoformat()
            }

            # Build session data
            session_data = {
                "id": active_session.id if active_session else None,
                "userId": user_id,
                "expiresAt": active_session.expires_at.isoformat() if active_session else None,
                "token": active_session.token if active_session else None,
                "sessionFingerprint": active_session.session_fingerprint if active_session else None,
                "createdAt": active_session.created_at.isoformat() if active_session else None,
                "updatedAt": active_session.updated_at.isoformat() if active_session else None,
                "ipAddress": active_session.ip_address if active_session else None,
                "userAgent": active_session.user_agent if active_session else None,
                "impersonatedBy": active_session.impersonated_by if active_session else None,
                "deviceInfo": json.loads(active_session.device_info) if active_session and active_session.device_info and isinstance(active_session.device_info, str) else (active_session.device_info if active_session and active_session.device_info else None),
                "lastActivity": active_session.last_activity.isoformat() if active_session and active_session.last_activity else None,
                "isTrusted": active_session.is_trusted if active_session else False,
                "securityLevel": active_session.security_level if active_session else "normal",
                "isActive": active_session.is_active if active_session else False
            }

            # Build user_vendor data
            user_vendor_data = {
                "vendor_id": vendor.id,
                "role": user_vendor.role.value if hasattr(user_vendor.role, 'value') else str(user_vendor.role),
                "can_scan_tickets": user_vendor.can_scan_tickets,
                "can_manage_content": user_vendor.can_manage_content,
                "vendor": {
                    "business_name": vendor.business_name,
                    "phone": vendor.phone,
                    "email": vendor.email,
                    "registration_status": vendor.registration_status.value if hasattr(vendor.registration_status, 'value') else str(vendor.registration_status),
                    "account_status": vendor.account_status.value if hasattr(vendor.account_status, 'value') else str(vendor.account_status)
                }
            }

            # Get permissions from user roles
            user_roles = await prisma.rbacuserrole.find_many(
                where={
                    "user_id": user_id,
                    "is_active": True
                },
                include={
                    "role": True
                }
            )

            permissions = []
            for user_role in user_roles:
                if not user_role.expires_at or user_role.expires_at > datetime.now(UTC):
                    if user_role.role.permissions:
                        permissions.extend(user_role.role.permissions)

            permissions = sorted(list(set(permissions)))

            # Build response data
            response_data = {
                "access_token": access_token,
                "refresh_token": new_refresh_token,
                "expires_in": settings.access_token_expire_minutes * 60,
                "refresh_expires_in": settings.refresh_token_expire_days * 24 * 60 * 60,
                "user": user_data,
                "session": session_data,
                "user_vendor": user_vendor_data,
                "permissions": permissions
            }

            return create_success_response(
                data=response_data,
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
            
            # Extract expiration time from the JWT token
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
            from app.main import logger
            logger.warning(f"Failed to store refresh token: {e}")


async def refresh_vendor_token_endpoint(
    refresh_data: RefreshTokenRequest, 
    request: Request
) -> Dict[str, Any]:
    """Endpoint handler for vendor token refresh"""
    try:
        result = await VendorRefreshTokenService.refresh_access_token(
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
                elif error_code == "NOT_A_VENDOR":
                    status_code = status.HTTP_403_FORBIDDEN
                elif error_code == "VENDOR_NOT_APPROVED":
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

