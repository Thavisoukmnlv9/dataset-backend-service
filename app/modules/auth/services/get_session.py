from typing import Dict, Any
from datetime import datetime, UTC
from fastapi import HTTPException, status
from app.prisma import prisma
from app.shared.utils.responses.response import create_success_response


async def get_session(user_id: str) -> Dict[str, Any]:
    """Get comprehensive user session information including user data, session data, and permissions"""
    try:
        # Get user information
        user = await prisma.user.find_unique(where={"id": user_id})

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # No need to get account info since we're using User model directly

        # Get active session
        active_session = await prisma.session.find_first(
            where={
                "user_id": user_id,
                "is_active": True,
                "expires_at": {"gt": datetime.now(UTC)}
            }
        )
        



        # Build user data from User model directly
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
            "deviceInfo": active_session.device_info if active_session else None,
            "lastActivity": active_session.last_activity.isoformat() if active_session and active_session.last_activity else None,
            "isTrusted": active_session.is_trusted if active_session else False,
            "securityLevel": active_session.security_level if active_session else "normal",
            "isActive": active_session.is_active if active_session else False
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
                permissions.extend(user_role.role.permissions)

        permissions = sorted(list(set(permissions)))

        session_response = {
            "user": user_data,
            "session": session_data,
            "permissions": permissions
        }

        return create_success_response(
            data=session_response,
            message="Session information retrieved successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        error_message = str(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving session information: {error_message}"
        )