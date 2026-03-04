import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile

from app.api.dependencies import get_current_active_user, get_admin_user
from app.shared.schemas.base import PaginationParams

from app.modules.cafes.schemas.cafe import (
    CafeCreate,
    CafeUpdate,
    CafeFilters,
    ListingStatusEnum,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cafes", tags=["Cafes"])

_FORM_JSON_KEYS = frozenset({
    "vendor", "languages_supported", "gallery_urls", "tags", "hours", "weekly_schedule",
    "media", "policies", "translations", "category_details", "rag_sources",
    "accessibility_features", "menu",
})

_MENU_IMAGE_PATTERN = re.compile(r"^menu\.sections\[(\d+)\]\.items\[(\d+)\]\.image_file(?:\[(\d+)\])?$")


def _is_upload_file(value: Any) -> bool:
    return hasattr(value, "read") and hasattr(value, "filename")


def _parse_form_payload(form: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for key, value in form.items():
        if _is_upload_file(value):
            continue
        if not isinstance(value, str):
            payload[key] = value
            continue
        if key in _FORM_JSON_KEYS and value.strip():
            try:
                payload[key] = json.loads(value)
            except json.JSONDecodeError:
                payload[key] = value
        else:
            payload[key] = value
    return payload


def _collect_files_from_form(form: Dict[str, Any]) -> Tuple[Optional[UploadFile], List[UploadFile], Optional[UploadFile], Dict[Tuple[int, int], List[UploadFile]]]:
    """Extract cover_image_file, gallery files, menu_source_file, menu item image files."""
    cover_file: Optional[UploadFile] = None
    gallery_list: List[UploadFile] = []
    menu_source_file: Optional[UploadFile] = None
    menu_item_by_index: Dict[Tuple[int, int], Dict[int, UploadFile]] = {}
    for key, value in form.items():
        if not _is_upload_file(value):
            continue
        if key in ("cover_image_file", "cover_image", "coverImageFile"):
            cover_file = value
        elif key == "menu_source_file":
            menu_source_file = value
        elif key == "gallery_files" or (key.startswith("gallery_") and key[8:].isdigit()):
            gallery_list.append(value)
        else:
            m = _MENU_IMAGE_PATTERN.match(key)
            if m:
                sec_idx = int(m.group(1))
                item_idx = int(m.group(2))
                file_idx = int(m.group(3)) if m.group(3) is not None else 0
                k = (sec_idx, item_idx)
                if k not in menu_item_by_index:
                    menu_item_by_index[k] = {}
                menu_item_by_index[k][file_idx] = value
    if "gallery_files" in form and _is_upload_file(form.get("gallery_files")):
        gallery_list = [form["gallery_files"]]
    menu_item_files_clean: Dict[Tuple[int, int], List[UploadFile]] = {}
    for k, by_idx in menu_item_by_index.items():
        menu_item_files_clean[k] = [by_idx[i] for i in sorted(by_idx)]
    return cover_file, gallery_list, menu_source_file, menu_item_files_clean


@router.get("", summary="List cafes")
async def list_cafes(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort: Optional[str] = Query("created_at"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    search: Optional[str] = Query(None),
    province: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    status: Optional[ListingStatusEnum] = Query(None),
    sub_category: Optional[str] = Query(None),
    _user=Depends(get_current_active_user),
):
    from app.modules.cafes.services.get_list import get_cafes

    filters = CafeFilters(province=province, district=district, status=status, sub_category=sub_category)
    pagination = PaginationParams(page=page, limit=limit, sort=sort, order=order)
    return await get_cafes(filters=filters, pagination=pagination, search=search)


@router.get("/{cafe_id}", summary="Get cafe by ID")
async def get_cafe_route(cafe_id: str, _user=Depends(get_current_active_user)):
    from app.modules.cafes.services.get_one import get_cafe as _get_one

    return await _get_one(cafe_id)


@router.post(
    "",
    summary="Create cafe (JSON or multipart/form-data)",
    description="Create cafe. Send JSON body or multipart/form-data with data=JSON string and optional cover_image_file, gallery_files.",
)
async def create_cafe_route(request: Request, admin_user=Depends(get_admin_user)):
    from app.modules.cafes.services.create import create_cafe as _create

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        payload = body
        cover_file, gallery_files = None, []
        menu_source_file, menu_item_files = None, {}
    else:
        form = await request.form()
        form_dict = dict(form)
        if "data" in form_dict and not _is_upload_file(form_dict.get("data")):
            payload = json.loads(form_dict["data"])
        else:
            payload = _parse_form_payload(form_dict)
        cover_file, gallery_files, menu_source_file, menu_item_files = _collect_files_from_form(form_dict)

    cafe_data = CafeCreate.model_validate(payload)
    return await _create(
        cafe_data,
        cover_image_file=cover_file,
        gallery_files=gallery_files,
        menu_source_file=menu_source_file,
        menu_item_files=menu_item_files,
    )


@router.put("/{cafe_id}", summary="Update cafe")
async def update_cafe_route(
    cafe_id: str,
    data: str = Form(..., description="JSON string of partial update (CafeUpdate)"),
    cover_image_file: Optional[UploadFile] = File(None),
    menu_source_file: Optional[UploadFile] = File(None),
    gallery_0: Optional[UploadFile] = File(None),
    gallery_1: Optional[UploadFile] = File(None),
    gallery_2: Optional[UploadFile] = File(None),
    admin_user=Depends(get_admin_user),
):
    from app.modules.cafes.services.update import update_cafe as _update

    payload = json.loads(data)
    update_data = CafeUpdate.model_validate(payload)
    gallery_files = [f for f in [gallery_0, gallery_1, gallery_2] if f and getattr(f, "filename", None)]
    return await _update(
        cafe_id,
        update_data,
        cover_image_file=cover_image_file,
        menu_source_file=menu_source_file,
        gallery_files=gallery_files,
    )


@router.delete("/{cafe_id}", summary="Delete cafe")
async def delete_cafe_route(cafe_id: str, admin_user=Depends(get_admin_user)):
    from app.modules.cafes.services.delete import delete_cafe as _delete

    return await _delete(cafe_id)
