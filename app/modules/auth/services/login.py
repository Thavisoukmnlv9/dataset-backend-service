from typing import Dict, Any
from datetime import datetime, timedelta, UTC
from fastapi import HTTPException, status, Request
from app.core.security import verify_password, create_access_token, create_refresh_token
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
from app.prisma import prisma, ensure_connection
from app.shared.utils.responses.response import create_success_response, create_error_response
from app.modules.auth.schemas.auth import UserLogin


class EmailLoginService:
    @staticmethod
    async def authenticate_user(
        email: str,
        password: str,
        request: Request
    ) -> Dict[str, Any]:
        """Authenticate user and return access and refresh tokens"""
        logger.info("Authenticating user %s", email)
        try:
            # Ensure database connection before querying
            await ensure_connection()
            
            user = await prisma.user.find_unique(where={"email": email})
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

            current_time = datetime.now(UTC)
            await prisma.user.update(
                where={"id": user.id},
                data={
                    "last_login_at": current_time,
                    "login_count": user.login_count + 1
                }
            )
            # No need to update account table since we're using User model directly
            access_token = create_access_token(data={"sub": str(user.id)})
            # Create refresh token using the standard function
            refresh_token = create_refresh_token(
                data={"sub": str(user.id), "type": "refresh"})
            await EmailLoginService._store_refresh_token(user.id, refresh_token, request)
            await EmailLoginService._create_session(user.id, request)
            # Build user data from User model directly
            user_data = {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "nickname": user.nickname,
                "role": user.role or "STAFF",
                "is_active": not user.banned,
                "last_login_at": current_time.isoformat(),
                "login_count": user.login_count + 1,
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
                    "refresh_token": refresh_token,
                    "expires_in": settings.access_token_expire_minutes * 60,
                    "refresh_expires_in": settings.refresh_token_expire_days * 24 * 60 * 60,
                    "user": user_data
                },
                message="Login successful"
            )

        except Exception as e:
            error_message = str(e)
            logger.error(f"Authentication error for user {email}: {error_message}", exc_info=True)
            
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
            logger.warning("Failed to store refresh token: %s", e)

    @staticmethod
    async def _create_session(user_id: str, request: Request) -> None:
        """Create a session for device tracking"""
        try:
            import json
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
            await prisma.session.create(
                data={
                    "user_id": user_id,
                    "token": session_token,
                    "session_fingerprint": session_fingerprint,
                    "expires_at": datetime.now(UTC) + timedelta(hours=24),
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "is_active": True,
                    # Explicitly serialize to JSON string
                    "device_info": json.dumps(device_info),
                    "last_activity": datetime.now(UTC),
                    "is_trusted": False,
                    "security_level": "normal"
                }
            )

        except Exception as e:
            logger.warning("Failed to create session for user %s: %s", user_id, e)
            raise


async def login_user_email(user_data: UserLogin, request: Request):
    try:
        result = await EmailLoginService.authenticate_user(
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
            detail=f"Error authenticating user: {error_message}"
        )
