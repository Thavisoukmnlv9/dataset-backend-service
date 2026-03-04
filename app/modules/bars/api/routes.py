import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile

from app.api.dependencies import get_current_active_user, get_admin_user
from app.shared.schemas.base import PaginationParams

from app.modules.bars.schemas.bar import (
    BarCreate,
    BarUpdate,
    BarFilters,
    ListingStatusEnum,
    ListingCategoryEnum,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bars", tags=["Bars"])

_FORM_JSON_KEYS = frozenset({
    "languages_supported", "gallery_urls", "gallery_files", "gallery_descriptions", "tags", "hours", "opening_hours",
    "policies", "translations", "menu", "category_details",
})

_GALLERY_FILE_PATTERN = re.compile(r"^gallery_urls\.url_file\[(\d+)\]$")
_GALLERY_FILES_IMAGE_PATTERN = re.compile(r"^gallery_files\[(\d+)\]\.image$")
_GALLERY_FILES_FILE_PATTERN = re.compile(r"^gallery_files\[(\d+)\]\.file$")
_MENU_IMAGE_PATTERN = re.compile(r"^menu\.sections\[(\d+)\]\.items\[(\d+)\]\.image_file(?:\[(\d+)\])?$")


def _is_upload_file(value: Any) -> bool:
    return hasattr(value, "read") and hasattr(value, "filename")


def _strip_trailing_json_comma(s: str) -> str:
    s = s.strip()
    if s.endswith(","):
        return s[:-1].strip()
    return s


def _normalize_json_string(s: str) -> str:
    s = s.strip()
    if not s:
        return s
    if s.startswith('"') and ":" in s[:30]:
        colon = s.find(":", 1)
        if colon != -1:
            rest = s[colon + 1:].lstrip()
            if rest.startswith("{"):
                depth = 0
                for i, c in enumerate(rest):
                    if c == "{":
                        depth += 1
                    elif c == "}":
                        depth -= 1
                        if depth == 0:
                            return rest[: i + 1].rstrip().rstrip(",").strip()
            elif rest.startswith("["):
                depth = 0
                for i, c in enumerate(rest):
                    if c == "[":
                        depth += 1
                    elif c == "]":
                        depth -= 1
                        if depth == 0:
                            return rest[: i + 1].rstrip().rstrip(",").strip()
    return s


def _parse_flat_form(form: Dict[str, Any]) -> Dict[str, Any]:
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
                stripped = _strip_trailing_json_comma(value)
                try:
                    payload[key] = json.loads(stripped)
                except json.JSONDecodeError:
                    normalized = _normalize_json_string(value)
                    normalized = _strip_trailing_json_comma(normalized) if normalized else normalized
                    try:
                        payload[key] = json.loads(normalized) if normalized else value
                    except json.JSONDecodeError:
                        payload[key] = value
        else:
            payload[key] = value
    return payload


def _collect_files_from_form(form: Dict[str, Any]) -> Tuple[
    Optional[UploadFile],
    List[UploadFile],
    Optional[UploadFile],
    Dict[Tuple[int, int], List[UploadFile]],
]:
    cover_file: Optional[UploadFile] = None
    gallery_by_index: Dict[int, UploadFile] = {}
    menu_source_file: Optional[UploadFile] = None
    menu_item_by_index: Dict[Tuple[int, int], Dict[int, UploadFile]] = {}

    _COVER_KEYS = frozenset({"cover_image_file", "cover_image", "coverImageFile", "cover_image_url"})

    gallery_files_list: List[UploadFile] = []
    for key, value in form.items():
        if key == "gallery_files" and _is_upload_file(value):
            gallery_files_list.append(value)

    for key, value in form.items():
        if not _is_upload_file(value):
            continue
        if key in _COVER_KEYS:
            cover_file = value
        elif key == "menu_source_file":
            menu_source_file = value
        elif key == "gallery_files":
            continue
        elif key.startswith("gallery_") and key[8:].isdigit():
            gallery_by_index[int(key[8:])] = value
        else:
            m = _GALLERY_FILE_PATTERN.match(key)
            if m:
                gallery_by_index[int(m.group(1))] = value
                continue
            m = _GALLERY_FILES_IMAGE_PATTERN.match(key)
            if m:
                gallery_by_index[int(m.group(1))] = value
                continue
            m = _GALLERY_FILES_FILE_PATTERN.match(key)
            if m:
                gallery_by_index[int(m.group(1))] = value
                continue
            m = _MENU_IMAGE_PATTERN.match(key)
            if m:
                sec_idx = int(m.group(1))
                item_idx = int(m.group(2))
                file_idx = int(m.group(3)) if m.group(3) is not None else 0
                k = (sec_idx, item_idx)
                if k not in menu_item_by_index:
                    menu_item_by_index[k] = {}
                menu_item_by_index[k][file_idx] = value

    if gallery_files_list:
        gallery_ordered = gallery_files_list
    else:
        gallery_ordered = [gallery_by_index[i] for i in sorted(gallery_by_index)]
    menu_item_files_clean: Dict[Tuple[int, int], List[UploadFile]] = {}
    for k, by_idx in menu_item_by_index.items():
        menu_item_files_clean[k] = [by_idx[i] for i in sorted(by_idx)]
    return cover_file, gallery_ordered, menu_source_file, menu_item_files_clean


@router.get("", summary="List bars")
async def list_bars(
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
    from app.modules.bars.services.get_list import get_bars

    filters = BarFilters(province=province, district=district, status=status, category=category)
    pagination = PaginationParams(page=page, limit=limit, sort=sort, order=order)
    return await get_bars(filters=filters, pagination=pagination, search=search)


@router.get("/{bar_id}", summary="Get bar by ID")
async def get_bar_route(bar_id: str, _user=Depends(get_current_active_user)):
    from app.modules.bars.services.get_one import get_bar

    return await get_bar(bar_id)


@router.post(
    "",
    summary="Create bar (multipart/form-data)",
    description="Create bar. Send multipart/form-data: either (1) data=JSON string + file fields, or (2) flat form fields + JSON strings for gallery_urls, tags, hours, menu, etc. + file fields.",
)
async def create_bar_route(request: Request, admin_user=Depends(get_admin_user)):
    from app.modules.bars.services.create import create_bar as _create

    form = await request.form()
    form_dict = dict(form)

    if "data" in form_dict and not _is_upload_file(form_dict.get("data")):
        data_str = form_dict["data"]
        payload = json.loads(data_str)
        cover_file, gallery_ordered, menu_source_file, menu_item_files = _collect_files_from_form(form)
    else:
        payload = _parse_flat_form(form_dict)
        cover_file, gallery_ordered, menu_source_file, menu_item_files = _collect_files_from_form(form)

    bar_data = BarCreate.model_validate(payload)
    return await _create(
        bar_data,
        cover_image_file=cover_file,
        menu_source_file=menu_source_file,
        gallery_files=gallery_ordered,
        menu_item_files=menu_item_files,
    )


@router.put("/{bar_id}", summary="Update bar")
async def update_bar_route(
    bar_id: str,
    data: str = Form(..., description="JSON string of partial update (BarUpdate)"),
    cover_image_file: Optional[UploadFile] = File(None),
    menu_source_file: Optional[UploadFile] = File(None),
    gallery_0: Optional[UploadFile] = File(None),
    gallery_1: Optional[UploadFile] = File(None),
    gallery_2: Optional[UploadFile] = File(None),
    admin_user=Depends(get_admin_user),
):
    from app.modules.bars.services.update import update_bar as _update

    payload = json.loads(data)
    update_data = BarUpdate.model_validate(payload)
    gallery_files = [f for f in [gallery_0, gallery_1, gallery_2] if f and f.filename]
    return await _update(
        bar_id,
        update_data,
        cover_image_file=cover_image_file,
        menu_source_file=menu_source_file,
        gallery_files=gallery_files,
    )


@router.delete("/{bar_id}", summary="Delete bar")
async def delete_bar_route(bar_id: str, admin_user=Depends(get_admin_user)):
    from app.modules.bars.services.delete import delete_bar as _delete

    return await _delete(bar_id)
