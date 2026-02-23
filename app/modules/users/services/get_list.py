"""Service for getting users list with filtering and pagination"""
import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from app.prisma import prisma
from app.modules.users.schemas.user import UserFilters
from app.shared.utils.responses.response import create_list_response
from app.shared.schemas.base import PaginationParams
from app.shared.services.infrastructure.storage import storage_service
import json

logger = logging.getLogger(__name__)


async def get_users(
    filters: UserFilters,
    pagination: PaginationParams,
    search_query: Optional[str] = None,
    sort_json: Optional[str] = None,
    filters_json: Optional[str] = None
) -> Dict[str, Any]:
    """Get users with filtering, pagination, and search"""
    try:
        validate_pagination(pagination.page, pagination.limit)

        # Parse filters from frontend if provided
        if filters_json:
            parsed_filters, extracted_search = parse_filters_from_frontend(
                filters_json)
            # Use extracted search if no search parameter provided
            if not search_query and extracted_search:
                search_query = extracted_search
        else:
            parsed_filters = filters

        # Build where clause with search if provided
        if search_query:
            where_clause = build_search_where_clause(
                search_query, parsed_filters)
        else:
            where_clause = build_where_clause(parsed_filters, search_query)

        # Parse sort from frontend
        sort_clause = parse_sort_from_frontend(
            sort_json) if sort_json else None

        # Query users
        users = await prisma.user.find_many(
            where=where_clause,
            order=get_order_clause(
                sort_by=sort_clause.get('field') if sort_clause else None,
                sort_order=sort_clause.get(
                    'dir', 'desc') if sort_clause else 'desc'
            ),
            skip=pagination.skip,
            take=pagination.limit,
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
                }
            }
        )
        total_count = await prisma.user.count(where=where_clause)
        
        processed_users = []

        for user in users:
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
                } if user.user_roles and len(user.user_roles) > 0 else None
            }
            processed_users.append(user_data)

        return create_list_response(
            items=processed_users,
            total=total_count,
            page=pagination.page,
            limit=pagination.limit,
            offset=pagination.offset,
            message="Users retrieved successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving users: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving users: {str(e)}"
        )


async def search_users(
    search_query: str,
    filters: UserFilters,
    offset: int = 0,
    limit: int = 20
) -> Dict[str, Any]:
    """Search users with advanced filters"""
    try:
        # Validate pagination
        page = (offset // limit) + 1
        validate_pagination(page, limit)

        # Build where clause with search
        where_clause = build_search_where_clause(search_query, filters)

        # Query users
        users = await prisma.user.find_many(
            where=where_clause,
            skip=offset,
            take=limit,
            order=get_order_clause(),
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
                }
            }
        )

        # Get total count
        total_count = await prisma.user.count(where=where_clause)

        # Process users
        processed_users = []
        for user in users:
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
                } if user.user_roles and len(user.user_roles) > 0 else None
            }
            processed_users.append(user_data)

        return create_list_response(
            items=processed_users,
            total=total_count,
            page=page,
            limit=limit,
            offset=offset,
            message="User search completed successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching users: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching users: {str(e)}"
        )


def build_where_clause(filters: UserFilters, search_query: Optional[str] = None) -> Dict[str, Any]:
    """Build where clause for users filtering"""
    where_clause = {}

    # Basic filters
    if filters.email:
        where_clause["email"] = {
            "contains": filters.email, "mode": "insensitive"}
    if filters.phone_number:
        where_clause["phone_number"] = {
            "contains": filters.phone_number, "mode": "insensitive"}
    if filters.role:
        where_clause["role"] = filters.role.value if hasattr(filters.role, 'value') else filters.role
    if filters.type:
        where_clause["type"] = filters.type.value if hasattr(filters.type, 'value') else filters.type
    if filters.banned is not None:
        where_clause["banned"] = filters.banned
    if filters.is_anonymous is not None:
        where_clause["is_anonymous"] = filters.is_anonymous
    if filters.email_verified is not None:
        where_clause["email_verified"] = filters.email_verified
    if filters.phone_number_verified is not None:
        where_clause["phone_number_verified"] = filters.phone_number_verified
    if filters.is_active is not None:
        where_clause["is_active"] = filters.is_active

    # Date range filters
    if filters.created_from or filters.created_to:
        date_filter = {}
        if filters.created_from:
            date_filter["gte"] = filters.created_from
        if filters.created_to:
            date_filter["lte"] = filters.created_to
        where_clause["created_at"] = date_filter

    if filters.last_login_from or filters.last_login_to:
        login_filter = {}
        if filters.last_login_from:
            login_filter["gte"] = filters.last_login_from
        if filters.last_login_to:
            login_filter["lte"] = filters.last_login_to
        where_clause["last_login_at"] = login_filter

    return where_clause


def build_search_where_clause(
    search_query: Optional[str],
    filters: UserFilters
) -> Dict[str, Any]:
    """Build where clause for search with text search across related fields"""
    where_clause = build_where_clause(filters)

    if search_query:
        # Search across user fields
        search_conditions = [
            {"email": {"contains": search_query, "mode": "insensitive"}},
            {"phone_number": {"contains": search_query, "mode": "insensitive"}},
            {"first_name": {"contains": search_query, "mode": "insensitive"}},
            {"last_name": {"contains": search_query, "mode": "insensitive"}},
            {"nickname": {"contains": search_query, "mode": "insensitive"}},
            {"role": {"contains": search_query, "mode": "insensitive"}},
            {"profile": {
                "first_name": {"contains": search_query, "mode": "insensitive"}
            }},
            {"profile": {
                "last_name": {"contains": search_query, "mode": "insensitive"}
            }},
            {"tourist": {
                "first_name": {"contains": search_query, "mode": "insensitive"}
            }},
            {"tourist": {
                "last_name": {"contains": search_query, "mode": "insensitive"}
            }},
            {"vendor": {
                "business_name": {"contains": search_query, "mode": "insensitive"}
            }}
        ]

        # If we have other filters, combine them with AND
        if where_clause:
            # Create a new where clause that combines filters with search
            combined_where = {
                "AND": [
                    where_clause,
                    {"OR": search_conditions}
                ]
            }
            return combined_where
        else:
            # No other filters, just use OR for search
            where_clause["OR"] = search_conditions

    return where_clause


def get_order_clause(sort_by: Optional[str] = None, sort_order: str = "desc") -> Dict[str, str]:
    """Get order clause for users sorting"""
    if sort_by:
        return {sort_by: sort_order}
    return {"created_at": "desc"}


def parse_sort_from_frontend(sort_json: Optional[str]) -> Optional[Dict[str, str]]:
    """Parse sort parameters from frontend JSON"""
    if not sort_json:
        return None

    try:
        sort_data = json.loads(sort_json)
        if isinstance(sort_data, list) and len(sort_data) > 0:
            sort_item = sort_data[0]
            if isinstance(sort_item, dict) and 'field' in sort_item and 'dir' in sort_item:
                return {sort_item['field']: sort_item['dir']}
        elif isinstance(sort_data, dict) and 'field' in sort_data and 'dir' in sort_data:
            return {sort_data['field']: sort_data['dir']}
    except (json.JSONDecodeError, TypeError, KeyError):
        pass

    return None


def parse_filters_from_frontend(filters_json: str) -> tuple[UserFilters, Optional[str]]:
    """Parse frontend filter JSON string into UserFilters and extract search query"""
    try:
        filters_data = json.loads(filters_json)
        if not isinstance(filters_data, list):
            return UserFilters(), None

        user_filters = UserFilters()
        search_query = None

        for filter_condition in filters_data:
            if not isinstance(filter_condition, dict):
                continue

            field = filter_condition.get('field')
            op = filter_condition.get('op')
            value = filter_condition.get('value')

            if not field or not op:
                continue

            # Handle different field types and operations
            if field == 'search' and op == 'contains':
                # Extract search query from search filter
                search_query = value
            elif field == 'email' and op == 'contains':
                user_filters.email = value
            elif field == 'phone_number' and op == 'contains':
                user_filters.phone_number = value
            elif field == 'role' and op == 'eq':
                try:
                    from app.modules.users.schemas.user import UserRoleEnum
                    user_filters.role = UserRoleEnum(value)
                except ValueError:
                    user_filters.role = value
            elif field == 'type' and op == 'eq':
                try:
                    from app.modules.users.schemas.user import UserTypeEnum
                    user_filters.type = UserTypeEnum(value)
                except ValueError:
                    user_filters.type = value
            elif field == 'banned' and op == 'eq':
                user_filters.banned = value
            elif field == 'is_anonymous' and op == 'eq':
                user_filters.is_anonymous = value
            elif field == 'email_verified' and op == 'eq':
                user_filters.email_verified = value
            elif field == 'phone_number_verified' and op == 'eq':
                user_filters.phone_number_verified = value
            elif field == 'is_active' and op == 'eq':
                user_filters.is_active = value
            elif field == 'created_from' and op == 'gte':
                user_filters.created_from = value
            elif field == 'created_to' and op == 'lte':
                user_filters.created_to = value
            elif field == 'last_login_from' and op == 'gte':
                user_filters.last_login_from = value
            elif field == 'last_login_to' and op == 'lte':
                user_filters.last_login_to = value

        return user_filters, search_query

    except (json.JSONDecodeError, TypeError, KeyError) as e:
        # Return empty filters if parsing fails
        return UserFilters(), None


def validate_pagination(page: int, limit: int) -> None:
    """Validate pagination parameters"""
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page must be greater than 0"
        )
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 100"
        )
