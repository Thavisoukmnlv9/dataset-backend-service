"""
Restaurants API routes.

- POST /restaurants: create (FormData: data=JSON string, cover_image_file, menu_source_file, gallery_0, gallery_1, ...)
- GET /restaurants: list with filters and pagination
- GET /restaurants/search: vector (semantic) search via Qdrant
- GET /restaurants/{id}: get one
- PUT /restaurants/{id}: update (optional FormData with same file fields)
- DELETE /restaurants/{id}: delete
"""
import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from app.api.dependencies import get_current_active_user, get_admin_user
from app.shared.schemas.base import PaginationParams

from app.modules.restaurants.schemas.restaurant import (
    RestaurantCreate,
    RestaurantUpdate,
    RestaurantFilters,
    ListingStatusEnum,
    ListingCategoryEnum,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/restaurants", tags=["Restaurants"])


@router.get("", summary="List restaurants")
async def list_restaurants(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort: Optional[str] = Query("created_at"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    search: Optional[str] = Query(None),
    province: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    status: Optional[ListingStatusEnum] = Query(None),
    category: Optional[ListingCategoryEnum] = Query(None),
    _user=Depends(get_current_active_user),
):
    from app.modules.restaurants.services.get_list import get_restaurants

    filters = RestaurantFilters(province=province, district=district, status=status, category=category)
    pagination = PaginationParams(page=page, limit=limit, sort=sort, order=order)
    return await get_restaurants(filters=filters, pagination=pagination, search=search)


@router.get("/search", summary="Semantic (vector) search via Qdrant")
async def vector_search_restaurants(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=50),
    _user=Depends(get_current_active_user),
):
    from app.modules.restaurants.services.get_list import search_restaurants_vector

    return await search_restaurants_vector(query=q, limit=limit)


@router.get("/{restaurant_id}", summary="Get restaurant by ID")
async def get_restaurant(restaurant_id: str, _user=Depends(get_current_active_user)):
    from app.modules.restaurants.services.get_one import get_restaurant as _get_one

    return await _get_one(restaurant_id)


@router.post("", summary="Create restaurant (JSON + optional image uploads)")
async def create_restaurant(
    data: str = Form(..., description="JSON string of restaurant payload (see RestaurantCreate schema)"),
    cover_image_file: Optional[UploadFile] = File(None, description="Cover image → cover_image_url"),
    menu_source_file: Optional[UploadFile] = File(None, description="Menu PDF/image → menu.source_url"),
    gallery_0: Optional[UploadFile] = File(None),
    gallery_1: Optional[UploadFile] = File(None),
    gallery_2: Optional[UploadFile] = File(None),
    gallery_3: Optional[UploadFile] = File(None),
    gallery_4: Optional[UploadFile] = File(None),
    admin_user=Depends(get_admin_user),
):
    """
    Create restaurant. Send FormData with:
    - data: JSON string matching restaurant.json (RestaurantCreate).
    - cover_image_file: file for cover image (updates cover_image_url).
    - menu_source_file: file for menu (updates menu.source_url).
    - gallery_0, gallery_1, ...: optional gallery images (order preserved).
    Data is stored in PostgreSQL and indexed in Qdrant (embed_text + optional embed_image).
    """
    from app.modules.restaurants.services.create import create_restaurant as _create

    payload = json.loads(data)
    restaurant_data = RestaurantCreate.model_validate(payload)
    gallery_files = [f for f in [gallery_0, gallery_1, gallery_2, gallery_3, gallery_4] if f and f.filename]
    return await _create(
        restaurant_data,
        cover_image_file=cover_image_file,
        menu_source_file=menu_source_file,
        gallery_files=gallery_files,
    )


@router.put("/{restaurant_id}", summary="Update restaurant")
async def update_restaurant(
    restaurant_id: str,
    data: str = Form(..., description="JSON string of partial update (RestaurantUpdate)"),
    cover_image_file: Optional[UploadFile] = File(None),
    menu_source_file: Optional[UploadFile] = File(None),
    gallery_0: Optional[UploadFile] = File(None),
    gallery_1: Optional[UploadFile] = File(None),
    gallery_2: Optional[UploadFile] = File(None),
    admin_user=Depends(get_admin_user),
):
    from app.modules.restaurants.services.update import update_restaurant as _update

    payload = json.loads(data)
    update_data = RestaurantUpdate.model_validate(payload)
    gallery_files = [f for f in [gallery_0, gallery_1, gallery_2] if f and f.filename]
    return await _update(
        restaurant_id,
        update_data,
        cover_image_file=cover_image_file,
        menu_source_file=menu_source_file,
        gallery_files=gallery_files,
    )


@router.delete("/{restaurant_id}", summary="Delete restaurant")
async def delete_restaurant(restaurant_id: str, admin_user=Depends(get_admin_user)):
    from app.modules.restaurants.services.delete import delete_restaurant as _delete

    return await _delete(restaurant_id)
