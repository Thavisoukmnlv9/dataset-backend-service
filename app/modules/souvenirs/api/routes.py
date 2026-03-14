import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile

from app.api.dependencies import get_current_active_user, get_admin_user
from app.shared.schemas.base import PaginationParams

from app.modules.souvenirs.schemas.souvenir import (
    SouvenirCreate,
    SouvenirCreateDraft,
    SouvenirUpdate,
    SouvenirFilters,
    ListingStatusEnum,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/souvenirs", tags=["Souvenirs"])

_FORM_JSON_KEYS = frozenset({
    "vendor", "languages_supported", "gallery_urls", "gallery_files", "gallery_descriptions",
    "tags", "hours", "opening_hours", "weekly_schedule", "policies", "translations", "details", "products",
})

_GALLERY_FILE_PATTERN = re.compile(r"^gallery_urls\.url_file\[(\d+)\]$")
_GALLERY_FILES_IMAGE_PATTERN = re.compile(r"^gallery_files\[(\d+)\]\.image$")
_GALLERY_FILES_FILE_PATTERN = re.compile(r"^gallery_files\[(\d+)\]\.file$")
_PRODUCT_IMAGE_PATTERN = re.compile(r"^products\[(\d+)\]\.images\[(\d+)\]\.image_file$")


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
                    if c == "{": depth += 1
                    elif c == "}":
                        depth -= 1
                        if depth == 0:
                            return rest[: i + 1].rstrip().rstrip(",").strip()
            elif rest.startswith("["):
                depth = 0
                for i, c in enumerate(rest):
                    if c == "[": depth += 1
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


def _collect_files_from_form(form: Any) -> Tuple[Optional[UploadFile], List[UploadFile], Dict[Tuple[int, int], Any]]:
    """Collect cover file, ordered gallery files (supports multiple same key), and product image files.
    form should be the raw FormData so getlist('gallery_files') returns all entries."""
    cover_file: Optional[UploadFile] = None
    gallery_by_index: Dict[int, UploadFile] = {}
    product_image_files: Dict[Tuple[int, int], Any] = {}
    _COVER_KEYS = frozenset({"cover_image_file", "cover_image", "coverImageFile"})

    gallery_files_list: List[UploadFile] = []
    if hasattr(form, "getlist"):
        for value in form.getlist("gallery_files"):
            if _is_upload_file(value):
                gallery_files_list.append(value)

    for key, value in form.items():
        if not _is_upload_file(value):
            continue
        if key in _COVER_KEYS:
            cover_file = value
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
            m = _PRODUCT_IMAGE_PATTERN.match(key)
            if m:
                product_image_files[(int(m.group(1)), int(m.group(2)))] = value
    gallery_ordered = gallery_files_list if gallery_files_list else [gallery_by_index[i] for i in sorted(gallery_by_index)]
    return cover_file, gallery_ordered, product_image_files


@router.get("", summary="List souvenirs")
async def list_souvenirs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort: Optional[str] = Query("created_at"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    search: Optional[str] = Query(None),
    province: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    status: Optional[ListingStatusEnum] = Query(None),
    category: Optional[str] = Query(None),
    _user=Depends(get_current_active_user),
):
    from app.modules.souvenirs.services.get_list import get_souvenirs

    filters = SouvenirFilters(province=province, district=district, status=status, category=category)
    pagination = PaginationParams(page=page, limit=limit, sort=sort, order=order)
    return await get_souvenirs(filters=filters, pagination=pagination, search=search)


@router.get("/draft/{souvenir_id}", summary="Get draft souvenir by ID")
async def get_draft_souvenir_route(souvenir_id: str, _user=Depends(get_current_active_user)):
    from app.modules.souvenirs.services.get_one import get_souvenir_draft

    return await get_souvenir_draft(souvenir_id)


@router.patch("/draft/{souvenir_id}", summary="Update draft souvenir")
async def update_draft_souvenir_route(
    souvenir_id: str,
    data: SouvenirCreateDraft,
    admin_user=Depends(get_admin_user),
):
    from app.modules.souvenirs.services.update import update_souvenir_draft as _update_draft

    return await _update_draft(souvenir_id, data)


@router.post("/draft", summary="Create souvenir (draft)")
async def create_souvenir_draft_route(
    data: SouvenirCreateDraft,
    admin_user=Depends(get_admin_user),
):
    from app.modules.souvenirs.services.create import create_souvenir_draft as _create_draft

    return await _create_draft(data)


@router.get("/{souvenir_id}", summary="Get souvenir by ID")
async def get_souvenir_route(souvenir_id: str, _user=Depends(get_current_active_user)):
    from app.modules.souvenirs.services.get_one import get_souvenir as _get_one

    return await _get_one(souvenir_id)


@router.post(
    "",
    summary="Create souvenir (multipart/form-data)",
    description="Create souvenir. Send multipart/form-data: either (1) data=JSON string + file fields, or (2) flat form fields + JSON strings for gallery_urls, tags, hours, details, products, etc. + file fields: cover_image_file, gallery_files, products[i].images[j].image_file for product images.",
)
async def create_souvenir_route(request: Request, admin_user=Depends(get_admin_user)):
    from app.modules.souvenirs.services.create import create_souvenir as _create

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        payload = body
        cover_file, gallery_files, product_image_files = None, [], {}
    else:
        form = await request.form()
        form_dict = dict(form)
        if "data" in form_dict and not _is_upload_file(form_dict.get("data")):
            data_str = form_dict["data"]
            payload = json.loads(data_str)
            cover_file, gallery_files, product_image_files = _collect_files_from_form(form)
        else:
            payload = _parse_flat_form(form_dict)
            cover_file, gallery_files, product_image_files = _collect_files_from_form(form)

    souvenir_data = SouvenirCreate.model_validate(payload)
    return await _create(
        souvenir_data,
        cover_image_file=cover_file,
        gallery_files=gallery_files,
        product_image_files=product_image_files,
    )


@router.put("/{souvenir_id}", summary="Update souvenir")
async def update_souvenir_route(
    souvenir_id: str,
    request: Request,
    admin_user=Depends(get_admin_user),
):
    from app.modules.souvenirs.services.update import update_souvenir as _update

    form = await request.form()
    form_dict = dict(form)
    data_str = form_dict.get("data")
    if not data_str or _is_upload_file(data_str):
        raise HTTPException(status_code=400, detail="data (JSON string) required")
    payload = json.loads(data_str)
    update_data = SouvenirUpdate.model_validate(payload)

    cover_file: Optional[UploadFile] = None
    gallery_files: List[UploadFile] = []
    if hasattr(form, "getlist"):
        gallery_files = [v for v in form.getlist("gallery_files") if _is_upload_file(v)]
    if not gallery_files:
        gallery_by_idx: Dict[int, UploadFile] = {}
        for key, value in form.items():
            if _is_upload_file(value) and key.startswith("gallery_") and key[8:].isdigit():
                gallery_by_idx[int(key[8:])] = value
        gallery_files = [gallery_by_idx[i] for i in sorted(gallery_by_idx)]
    for key, value in form.items():
        if _is_upload_file(value) and key in frozenset({"cover_image_file", "cover_image", "coverImageFile"}):
            cover_file = value
            break

    return await _update(
        souvenir_id,
        update_data,
        cover_image_file=cover_file,
        gallery_files=gallery_files,
    )


@router.delete("/{souvenir_id}", summary="Delete souvenir")
async def delete_souvenir_route(souvenir_id: str, admin_user=Depends(get_admin_user)):
    from app.modules.souvenirs.services.delete import delete_souvenir as _delete

    return await _delete(souvenir_id)
