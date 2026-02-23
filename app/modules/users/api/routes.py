"""
Users API routes.

Thin route layer — delegates all business logic to service functions.
No direct DB calls here.
"""
import json
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from app.api.dependencies import (
    get_current_active_user,
    get_admin_user,
    get_super_admin_user,
)
from app.modules.users.schemas.user import (
    UserFilters,
    UserUpdate,
    UserBanUpdate,
    UserRoleEnum,
    UserFormDataCreate,
    UserRoleCreateData,
    UserLookupQueryDTO,
)
from app.shared.schemas.base import PaginationParams

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


# ── Stats (before /{user_id} so it doesn't shadow) ──────────────────────────

@router.get("/stats", summary="Get user statistics")
async def user_stats(_admin=Depends(get_admin_user)):
    from app.modules.users.services.stats import get_user_stats
    return await get_user_stats()


# ── Lookup ───────────────────────────────────────────────────────────────────

@router.get("/lookup", summary="Lookup users for dropdowns")
async def lookup_users(
    q: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    _user=Depends(get_current_active_user),
):
    from app.modules.users.services.lookup import lookup_users as _lookup
    query = UserLookupQueryDTO(q=q, limit=limit, skip=skip)
    return await _lookup(query)


@router.get("/lookup/{user_id}", summary="Lookup single user by ID")
async def lookup_user_by_id(user_id: str, _user=Depends(get_current_active_user)):
    from app.modules.users.services.lookup import lookup_user_by_id as _lookup_by_id
    return await _lookup_by_id(user_id)


# ── List / Search ────────────────────────────────────────────────────────────

@router.get("", summary="List users with filtering and pagination")
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort: Optional[str] = Query("created_at"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    search: Optional[str] = Query(None),
    sort_json: Optional[str] = Query(None, alias="sort_json"),
    filters_json: Optional[str] = Query(None, alias="filters_json"),
    role: Optional[UserRoleEnum] = Query(None),
    banned: Optional[bool] = Query(None),
    is_active: Optional[bool] = Query(None),
    email_verified: Optional[bool] = Query(None),
    _admin=Depends(get_admin_user),
):
    from app.modules.users.services.get_list import get_users

    filters = UserFilters(
        role=role,
        banned=banned,
        is_active=is_active,
        email_verified=email_verified,
    )
    pagination = PaginationParams(page=page, limit=limit, sort=sort, order=order)
    return await get_users(
        filters=filters,
        pagination=pagination,
        search_query=search,
        sort_json=sort_json,
        filters_json=filters_json,
    )


@router.get("/search", summary="Search users")
async def search_users(
    q: str = Query(..., min_length=1),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    _admin=Depends(get_admin_user),
):
    from app.modules.users.services.get_list import search_users as _search

    filters = UserFilters()
    return await _search(search_query=q, filters=filters, offset=offset, limit=limit)


# ── CRUD ─────────────────────────────────────────────────────────────────────

@router.get("/{user_id}", summary="Get user by ID")
async def get_user(user_id: UUID, _user=Depends(get_current_active_user)):
    from app.modules.users.services.get_one import get_user as _get_user
    return await _get_user(user_id)


@router.post("", summary="Create user (admin)")
async def create_user(
    email: str = Form(...),
    password: Optional[str] = Form(None),
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    role: Optional[UserRoleEnum] = Form(None),
    is_anonymous: bool = Form(False),
    email_verified: bool = Form(False),
    phone_number_verified: bool = Form(False),
    user_roles_json: Optional[str] = Form(None),
    avatar: Optional[UploadFile] = File(None),
    admin_user=Depends(get_admin_user),
):
    from app.modules.users.services.create import create_user_with_form_data_and_image

    user_roles = None
    if user_roles_json:
        parsed = json.loads(user_roles_json)
        user_roles = [UserRoleCreateData(**r) for r in parsed]

    user_data = UserFormDataCreate(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        phone_number=phone_number,
        role=role,
        is_anonymous=is_anonymous,
        email_verified=email_verified,
        phone_number_verified=phone_number_verified,
        user_roles=user_roles,
    )
    return await create_user_with_form_data_and_image(
        user_data, avatar, admin_user.id
    )


@router.put("/{user_id}", summary="Update user")
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    _admin=Depends(get_admin_user),
):
    from app.modules.users.services.update import update_user as _update
    return await _update(user_id, user_data)


@router.put("/{user_id}/ban", summary="Ban or unban user")
async def ban_user(
    user_id: UUID,
    ban_data: UserBanUpdate,
    _admin=Depends(get_admin_user),
):
    from app.modules.users.services.update import ban_user as _ban
    return await _ban(user_id, ban_data)


@router.put("/{user_id}/verify-email", summary="Admin verify user email")
async def verify_user_email(user_id: UUID, _admin=Depends(get_admin_user)):
    from app.modules.users.services.update import verify_user_email as _verify
    return await _verify(user_id)


@router.put("/{user_id}/verify-phone", summary="Admin verify user phone")
async def verify_user_phone(user_id: UUID, _admin=Depends(get_admin_user)):
    from app.modules.users.services.update import verify_user_phone as _verify
    return await _verify(user_id)


# ── Delete / Restore ─────────────────────────────────────────────────────────

@router.delete("/{user_id}", summary="Soft-delete user")
async def delete_user(user_id: UUID, _admin=Depends(get_admin_user)):
    from app.modules.users.services.delete import delete_user as _delete
    return await _delete(user_id)


@router.post("/{user_id}/restore", summary="Restore soft-deleted user")
async def restore_user(user_id: UUID, _admin=Depends(get_admin_user)):
    from app.modules.users.services.delete import restore_user as _restore
    return await _restore(user_id)


@router.delete("/{user_id}/hard", summary="Permanently delete user (super-admin)")
async def hard_delete_user(user_id: UUID, _admin=Depends(get_super_admin_user)):
    from app.modules.users.services.delete import hard_delete_user as _hard_delete
    return await _hard_delete(user_id)
