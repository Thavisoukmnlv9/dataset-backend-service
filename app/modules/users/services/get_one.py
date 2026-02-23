"""Service for getting a single user"""
import logging
from typing import Dict, Any
from uuid import UUID
from fastapi import HTTPException, status
from app.prisma import prisma
from app.shared.utils.responses.response import create_success_response
from app.shared.services.infrastructure.storage import storage_service

logger = logging.getLogger(__name__)


async def get_user(user_id: UUID) -> Dict[str, Any]:
    """Get a user by ID"""
    try:
        user = await prisma.user.find_unique(
            where={"id": str(user_id)},
            include={
                "profile": True,
                "tourist": True,
                "vendor": {
                    "include": {
                        "business": True
                    }
                },
                "wallet": True,
                "user_roles": {
                    "include": {
                        "role": True
                    }
                },
                "sessions": {
                    "where": {"is_active": True},
                    "order_by": {"created_at": "desc"},
                    "take": 5
                }
            }
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Process user avatar
        processed_avatar = None
        avatar_url_image = None
        if user.avatar_url:
            resized_urls = await storage_service.get_resized_image_urls(user.avatar_url)
            # Prefer medium size, fallback to large, small, or any available size
            processed_avatar = (
                resized_urls.get('medium') or 
                resized_urls.get('large') or 
                resized_urls.get('small') or 
                next((url for url in resized_urls.values() if url), None)
            )
            # Create avatar_url_image object with all sizes
            avatar_url_image = {
                "thumbnail": resized_urls.get('thumbnail'),
                "small": resized_urls.get('small'),
                "medium": resized_urls.get('medium'),
                "large": resized_urls.get('large')
            }

        # Process user data with related information
        user_data = {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "nickname": user.nickname,
            "country_code": user.country_code,
            "avatar_url": processed_avatar,
            "avatar_url_image": avatar_url_image,
            "language_pref": user.language_pref,
            "email_verified": user.email_verified,
            "email_verified_at": user.email_verified_at.isoformat() if user.email_verified_at else None,
            "phone_number_verified": user.phone_number_verified,
            "phone_number": user.phone_number,
            "theme_pref": user.theme_pref,
            "google_id": user.google_id,
            "facebook_id": user.facebook_id,
            "apple_id": user.apple_id,
            "social_provider": user.social_provider,
            "scope": user.scope,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "failed_login_attempts": user.failed_login_attempts,
            "locked_until": user.locked_until.isoformat() if user.locked_until else None,
            "role": user.role,
            "type": user.type,
            "banned": user.banned,
            "ban_reason": user.ban_reason,
            "ban_expires": user.ban_expires.isoformat() if user.ban_expires else None,
            "is_anonymous": user.is_anonymous,
            "last_logout_at": user.last_logout_at.isoformat() if user.last_logout_at else None,
            "login_count": user.login_count,
            "deleted_at": user.deleted_at.isoformat() if user.deleted_at else None,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
            "profile": {
                "id": str(user.profile.id),
                "first_name": user.profile.first_name,
                "last_name": user.profile.last_name,
                "nickname": user.profile.nickname,
                "date_of_birth": user.profile.date_of_birth.isoformat() if user.profile.date_of_birth else None,
                "gender": user.profile.gender,
                "nationality": user.profile.nationality,
                "address": user.profile.address,
                "city": user.profile.city,
                "state": user.profile.state,
                "country": user.profile.country,
                "postal_code": user.profile.postal_code,
                "created_at": user.profile.created_at.isoformat(),
                "updated_at": user.profile.updated_at.isoformat()
            } if user.profile else None,
            "tourist": {
                "id": str(user.tourist.id),
                "first_name": user.tourist.first_name,
                "last_name": user.tourist.last_name,
                "gender": user.tourist.gender,
                "date_of_birth": user.tourist.date_of_birth.isoformat() if user.tourist.date_of_birth else None,
                "nationality": user.tourist.nationality,
                "email": user.tourist.email,
                "phone_number": user.tourist.phone_number,
                "created_at": user.tourist.created_at.isoformat(),
                "updated_at": user.tourist.updated_at.isoformat()
            } if user.tourist else None,
            "vendor": {
                "id": str(user.vendor[0].id),
                "business_name": user.vendor[0].business.business_name,
                "business_name_lao": user.vendor[0].business.business_name_lao,
                "business_type": user.vendor[0].business.business_type,
                "contact_name": user.vendor[0].contact_name,
                "contact_email": user.vendor[0].contact_email,
                "contact_phone": user.vendor[0].contact_phone,
                "address": user.vendor[0].business.address,
                "city": user.vendor[0].business.city,
                "province": user.vendor[0].business.province,
                "status": user.vendor[0].status,
                "business_status": user.vendor[0].business.status,
                "created_at": user.vendor[0].created_at.isoformat(),
                "updated_at": user.vendor[0].updated_at.isoformat()
            } if user.vendor and len(user.vendor) > 0 else None,
            "wallet": {
                "id": str(user.wallet.id),
                "balance": float(user.wallet.balance),
                "currency": user.wallet.currency,
                "is_active": user.wallet.is_active,
                "created_at": user.wallet.created_at.isoformat(),
                "updated_at": user.wallet.updated_at.isoformat()
            } if user.wallet else None,
            "user_roles": {
                "role_id": str(user.user_roles[0].role_id),
                "business_id": str(user.user_roles[0].business_id),
                "assigned_at": user.user_roles[0].assigned_at.isoformat(),
                "expires_at": user.user_roles[0].expires_at.isoformat() if user.user_roles[0].expires_at else None,
                "is_active": user.user_roles[0].is_active,
                "role": {
                    "id": str(user.user_roles[0].role.id),
                    "name": user.user_roles[0].role.name,
                    "description": user.user_roles[0].role.description,
                    "permissions": user.user_roles[0].role.permissions,
                    "business_type": user.user_roles[0].role.business_type
                },
                "business_id": str(user.user_roles[0].business_id)
            } if user.user_roles and len(user.user_roles) > 0 else None,
            "recent_sessions": [
                {
                    "id": str(session.id),
                    "ip_address": session.ip_address,
                    "user_agent": session.user_agent,
                    "is_active": session.is_active,
                    "created_at": session.created_at.isoformat(),
                    "expires_at": session.expires_at.isoformat()
                }
                for session in user.sessions
            ]
        }

        return create_success_response(
            message="User retrieved successfully",
            data={"item": user_data}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user: {str(e)}"
        )
