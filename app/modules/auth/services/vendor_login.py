from typing import Dict, Any, Optional
from datetime import datetime, timedelta, UTC
from fastapi import HTTPException, status, Request
from app.core.security import verify_password, create_access_token, create_refresh_token
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
from app.prisma import prisma, ensure_connection
from app.shared.utils.responses.response import create_success_response, create_error_response
from app.modules.auth.schemas.auth import UserLogin
import json


class VendorLoginService:
    @staticmethod
    async def authenticate_vendor(
        email: str,
        password: str,
        request: Request
    ) -> Dict[str, Any]:
        """Authenticate vendor user and return access and refresh tokens with vendor-specific data"""
        logger.info(f"Authenticating vendor user {email}")
        try:
            # Ensure database connection before querying
            await ensure_connection()
            
            user = await prisma.user.find_unique(
                where={"email": email},
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
                    error_code="INVALID_CREDENTIALS",
                    message="Invalid email or password"
                )
            
            if user.banned:
                return create_error_response(
                    error_code="ACCOUNT_BANNED",
                    message="Account is banned"
                )
            
            # Check if user has a password set
            if not user.password:
                return create_error_response(
                    error_code="INVALID_CREDENTIALS",
                    message="Invalid email or password"
                )

            if not verify_password(password, user.password):
                return create_error_response(
                    error_code="INVALID_CREDENTIALS",
                    message="Invalid email or password"
                )

            # Check if user has a UserVendor relationship
            if not user.UserVendor or len(user.UserVendor) == 0:
                return create_error_response(
                    error_code="NOT_A_VENDOR",
                    message="User is not associated with any vendor"
                )

            # Get the first active UserVendor (assuming one vendor per user for now)
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

            current_time = datetime.now(UTC)
            await prisma.user.update(
                where={"id": user.id},
                data={
                    "last_login_at": current_time,
                    "login_count": user.login_count + 1
                }
            )
            
            # Create tokens
            access_token = create_access_token(data={"sub": str(user.id)})
            refresh_token = create_refresh_token(
                data={"sub": str(user.id), "type": "refresh"}
            )
            
            # Store refresh token and create session
            await VendorLoginService._store_refresh_token(user.id, refresh_token, request)
            session = await VendorLoginService._create_session(user.id, request)
            
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
                "last_login_at": current_time.isoformat(),
                "login_count": user.login_count + 1,
                "createdAt": user.created_at.isoformat(),
                "updatedAt": user.updated_at.isoformat()
            }

            # Build session data
            session_data = {
                "id": session.id if session else None,
                "userId": user.id,
                "expiresAt": session.expires_at.isoformat() if session else None,
                "token": session.token if session else None,
                "sessionFingerprint": session.session_fingerprint if session else None,
                "createdAt": session.created_at.isoformat() if session else None,
                "updatedAt": session.updated_at.isoformat() if session else None,
                "ipAddress": session.ip_address if session else None,
                "userAgent": session.user_agent if session else None,
                "impersonatedBy": session.impersonated_by if session else None,
                "deviceInfo": json.loads(session.device_info) if session and session.device_info and isinstance(session.device_info, str) else (session.device_info if session and session.device_info else None),
                "lastActivity": session.last_activity.isoformat() if session and session.last_activity else None,
                "isTrusted": session.is_trusted if session else False,
                "securityLevel": session.security_level if session else "normal",
                "isActive": session.is_active if session else False
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
                    "user_id": user.id,
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
                "refresh_token": refresh_token,
                "expires_in": settings.access_token_expire_minutes * 60,
                "refresh_expires_in": settings.refresh_token_expire_days * 24 * 60 * 60,
                "user": user_data,
                "session": session_data,
                "user_vendor": user_vendor_data,
                "permissions": permissions
            }

            return create_success_response(
                data=response_data,
                message="Vendor login successful"
            )

        except Exception as e:
            error_message = str(e)
            logger.error(f"Vendor authentication error for user {email}: {error_message}", exc_info=True)
            
            # Check if it's a connection error
            if "connection" in error_message.lower() or "connect" in error_message.lower():
                return create_error_response(
                    error_code="DATABASE_CONNECTION_ERROR",
                    message="Database connection failed. Please try again later."
                )
            
            return create_error_response(
                error_code="AUTHENTICATION_FAILED",
                message=f"Authentication failed: {error_message}"
            )

    @staticmethod
    async def _store_refresh_token(user_id: str, refresh_token: str, request: Request, expire_time: datetime = None) -> None:
        """Store our internal refresh token in RefreshToken model"""
        try:
            from app.core.security import hash_token
            import jwt

            # Use provided expiration time or decode from token
            if expire_time is None:
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
            logger.warning(f"Failed to store refresh token: {e}")

    @staticmethod
    async def _create_session(user_id: str, request: Request):
        """Create a session for device tracking"""
        try:
            user_agent = request.headers.get("user-agent", "")
            ip_address = request.client.host if request.client else None

            session_token = f"session_{user_id}_{datetime.now(UTC).timestamp()}"
            session_fingerprint = f"{ip_address}_{user_agent}_{datetime.now(UTC).timestamp()}"

            # Prepare device info as a proper JSON object
            device_info = {
                "user_agent": user_agent,
                "ip_address": ip_address,
                "login_time": datetime.now(UTC).isoformat()
            }
            
            session = await prisma.session.create(
                data={
                    "user_id": user_id,
                    "token": session_token,
                    "session_fingerprint": session_fingerprint,
                    "expires_at": datetime.now(UTC) + timedelta(hours=24),
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "is_active": True,
                    "device_info": json.dumps(device_info),
                    "last_activity": datetime.now(UTC),
                    "is_trusted": False,
                    "security_level": "normal"
                }
            )
            
            return session

        except Exception as e:
            logger.warning(f"Failed to create session for user {user_id}: {e}")
            return None


async def login_vendor_email(user_data: UserLogin, request: Request):
    try:
        result = await VendorLoginService.authenticate_vendor(
            user_data.email,
            user_data.password,
            request
        )

        if not result.success:
            if hasattr(result, 'error'):
                error_code = result.error.get("code", "AUTHENTICATION_FAILED")
                error_message = result.error.get(
                    "message", "Authentication failed")
                status_code = status.HTTP_401_UNAUTHORIZED
                if error_code == "ACCOUNT_BANNED":
                    status_code = status.HTTP_403_FORBIDDEN
                elif error_code == "NOT_A_VENDOR":
                    status_code = status.HTTP_403_FORBIDDEN
                elif error_code == "VENDOR_NOT_APPROVED":
                    status_code = status.HTTP_403_FORBIDDEN
                elif error_code == "DATABASE_CONNECTION_ERROR":
                    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
                elif error_code == "AUTHENTICATION_FAILED":
                    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

                raise HTTPException(
                    status_code=status_code,
                    detail=error_message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication failed"
                )
        return result

    except HTTPException:
        raise
    except Exception as e:
        error_message = str(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error authenticating vendor: {error_message}"
        )

