import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile

from app.api.dependencies import get_current_active_user, get_admin_user
from app.shared.schemas.base import PaginationParams

from app.modules.attractions.schemas.attraction import (
    AttractionCreate,
    AttractionCreateDraft,
    AttractionUpdate,
    AttractionProcessUpdate,
    AttractionFilters,
    ListingStatusEnum,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/attractions", tags=["Attractions"])

_FORM_JSON_KEYS = frozenset[str]({
    "languages_supported",
    "gallery_urls",
    "gallery_files",
    "gallery_descriptions",
    "tags",
    "hours",
    "opening_hours",
    "policies",
    "processes",
    "translations",
    "details",
})

_GALLERY_FILE_PATTERN = re.compile(r"^gallery_urls\.url_file\[(\d+)\]$")
_GALLERY_FILES_IMAGE_PATTERN = re.compile(r"^gallery_files\[(\d+)\]\.image$")
_GALLERY_FILES_FILE_PATTERN = re.compile(r"^gallery_files\[(\d+)\]\.file$")


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
            rest = s[colon + 1 :].lstrip()
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


def _collect_files_from_form(form: Dict[str, Any]) -> Tuple[Optional[UploadFile], List[UploadFile]]:
    cover_file: Optional[UploadFile] = None
    gallery_by_index: Dict[int, UploadFile] = {}

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

    if gallery_files_list:
        gallery_ordered = gallery_files_list
    else:
        gallery_ordered = [gallery_by_index[i] for i in sorted(gallery_by_index)]
    return cover_file, gallery_ordered


@router.get("", summary="List attractions")
async def list_attractions(
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
    from app.modules.attractions.services.get_list import get_attractions

    filters = AttractionFilters(province=province, district=district, status=status, category=category)
    pagination = PaginationParams(page=page, limit=limit, sort=sort, order=order)
    return await get_attractions(filters=filters, pagination=pagination, search=search)


@router.get("/draft/{attraction_id}", summary="Get draft attraction by ID")
async def get_draft_attraction_route(attraction_id: str, _user=Depends(get_current_active_user)):
    from app.modules.attractions.services.get_one import get_attraction_draft

    return await get_attraction_draft(attraction_id)


@router.patch(
    "/draft/{attraction_id}",
    summary="Update draft attraction",
    description="Update a draft attraction's minimal fields (name, location, contact). JSON body.",
)
async def update_draft_attraction_route(
    attraction_id: str,
    data: AttractionCreateDraft,
    admin_user=Depends(get_admin_user),
):
    from app.modules.attractions.services.update import update_attraction_draft as _update_draft

    return await _update_draft(attraction_id, data)


@router.get("/{attraction_id}", summary="Get attraction by ID")
async def get_attraction_route(attraction_id: str, _user=Depends(get_current_active_user)):
    from app.modules.attractions.services.get_one import get_attraction

    return await get_attraction(attraction_id)


@router.post(
    "/draft",
    summary="Create attraction (draft)",
    description="Create an attraction with: attraction_name, longitude, latitude, country, province, district, village, contact_phone. JSON body.",
)
async def create_attraction_draft_route(
    data: AttractionCreateDraft,
    admin_user=Depends(get_admin_user),
):
    from app.modules.attractions.services.create import create_attraction_draft as _create_draft

    return await _create_draft(data)


@router.post(
    "",
    summary="Create attraction (multipart/form-data)",
    description="Create attraction. Send multipart/form-data: either (1) data=JSON string + file fields, or (2) flat form fields + JSON strings for gallery_urls, tags, hours, details, etc. + file fields.",
)
async def create_attraction_route(request: Request, admin_user=Depends(get_admin_user)):
    from app.modules.attractions.services.create import create_attraction as _create

    form = await request.form()
    form_dict = dict(form)

    if "data" in form_dict and not _is_upload_file(form_dict.get("data")):
        data_str = form_dict["data"]
        payload = json.loads(data_str)
        if isinstance(payload, dict) and "data" in payload and isinstance(payload["data"], dict):
            inner = payload["data"]
            if "attraction" in inner and isinstance(inner["attraction"], dict):
                payload = inner["attraction"]
            else:
                payload = inner
        cover_file, gallery_ordered = _collect_files_from_form(form)
    else:
        payload = _parse_flat_form(form_dict)
        cover_file, gallery_ordered = _collect_files_from_form(form)

    attraction_data = AttractionCreate.model_validate(payload)
    return await _create(
        attraction_data,
        cover_image_file=cover_file,
        gallery_files=gallery_ordered,
    )


@router.put("/{attraction_id}", summary="Update attraction")
async def update_attraction_route(
    attraction_id: str,
    data: str = Form(..., description="JSON string of partial update (AttractionUpdate)"),
    cover_image_file: Optional[UploadFile] = File(None),
    gallery_0: Optional[UploadFile] = File(None),
    gallery_1: Optional[UploadFile] = File(None),
    gallery_2: Optional[UploadFile] = File(None),
    admin_user=Depends(get_admin_user),
):
    from app.modules.attractions.services.update import update_attraction as _update

    payload = json.loads(data)
    update_data = AttractionUpdate.model_validate(payload)
    gallery_files = [f for f in [gallery_0, gallery_1, gallery_2] if f and f.filename]
    return await _update(
        attraction_id,
        update_data,
        cover_image_file=cover_image_file,
        gallery_files=gallery_files,
    )


@router.delete("/{attraction_id}", summary="Delete attraction")
async def delete_attraction_route(attraction_id: str, admin_user=Depends(get_admin_user)):
    from app.modules.attractions.services.delete import delete_attraction as _delete

    return await _delete(attraction_id)


@router.patch(
    "/{attraction_id}/processes/{process_id}",
    summary="Update attraction process",
    description="Update a single process's status and/or result (e.g. set to TODO to retry).",
)
async def update_attraction_process_route(
    attraction_id: str,
    process_id: str,
    data: AttractionProcessUpdate,
    admin_user=Depends(get_admin_user),
):
    from app.modules.attractions.services.update import update_attraction_process as _update_process

    return await _update_process(attraction_id, process_id, data)
