import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile

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

# Form keys whose value is a JSON string (list or dict)
_FORM_JSON_KEYS = frozenset({
    "languages_supported", "gallery_urls", "tags", "hours", "policies",
    "translations", "menu", "category_details",
})

# Regex for gallery file keys: gallery_urls.url_file[0], gallery_urls.url_file[1], ...
_GALLERY_FILE_PATTERN = re.compile(r"^gallery_urls\.url_file\[(\d+)\]$")
# Regex for menu item image keys: menu.sections[0].items[1].image_file
_MENU_IMAGE_PATTERN = re.compile(r"^menu\.sections\[(\d+)\]\.items\[(\d+)\]\.image_file$")


def _is_upload_file(value: Any) -> bool:
    return hasattr(value, "read") and hasattr(value, "filename")


def _strip_trailing_json_comma(s: str) -> str:
    """Remove trailing comma after } or ] so '{"a":1},' or '[1,2],' becomes valid JSON."""
    s = s.strip()
    if s.endswith(","):
        return s[:-1].strip()
    return s


def _normalize_json_string(s: str) -> str:
    """If string looks like a JSON object fragment (e.g. ' "menu": { ... },'), extract the object part."""
    s = s.strip()
    if not s:
        return s
    # Strip leading "key": so we can parse the value (e.g. ' "menu": { ... },' -> '{ ... }')
    if s.startswith('"') and ":" in s[:30]:
        colon = s.find(":", 1)
        if colon != -1:
            rest = s[colon + 1 :].lstrip()
            if rest.startswith("{"):
                # Find matching closing brace and strip trailing comma
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
    """Build restaurant payload from flat form fields. Parses JSON for known complex keys."""
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
                # Try stripping trailing comma (e.g. '{"menu":...},' from form)
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
    Dict[Tuple[int, int], UploadFile],
]:
    """Extract cover_image_file, gallery files (ordered), menu_source_file, menu item image files."""
    cover_file: Optional[UploadFile] = None
    gallery_by_index: Dict[int, UploadFile] = {}
    menu_source_file: Optional[UploadFile] = None
    menu_item_files: Dict[Tuple[int, int], UploadFile] = {}

    for key, value in form.items():
        if not _is_upload_file(value):
            continue
        if key == "cover_image_file":
            cover_file = value
        elif key == "menu_source_file":
            menu_source_file = value
        elif key.startswith("gallery_") and key[8:].isdigit():
            gallery_by_index[int(key[8:])] = value
        else:
            m = _GALLERY_FILE_PATTERN.match(key)
            if m:
                gallery_by_index[int(m.group(1))] = value
                continue
            m = _MENU_IMAGE_PATTERN.match(key)
            if m:
                menu_item_files[(int(m.group(1)), int(m.group(2)))] = value

    gallery_ordered = [gallery_by_index[i] for i in sorted(gallery_by_index)]
    return cover_file, gallery_ordered, menu_source_file, menu_item_files


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


@router.post(
    "",
    summary="Create restaurant (multipart/form-data)",
    description="Create restaurant. Send multipart/form-data: either (1) data=JSON string + file fields, or (2) flat form fields + JSON strings for gallery_urls, tags, hours, menu, etc. + file fields: cover_image_file, gallery_urls.url_file[0], menu.sections[i].items[j].image_file.",
)
async def create_restaurant(request: Request, admin_user=Depends(get_admin_user)):
     
    from app.modules.restaurants.services.create import create_restaurant as _create
    
    form = await request.form()
    form_dict = dict(form)

    if "data" in form_dict and not _is_upload_file(form_dict["data"]):
        data_str = form_dict["data"]
        payload = json.loads(data_str)
        cover_file, gallery_ordered, menu_source_file, menu_item_files = _collect_files_from_form(form_dict)
    else:
        payload = _parse_flat_form(form_dict)
        cover_file, gallery_ordered, menu_source_file, menu_item_files = _collect_files_from_form(form_dict)

    restaurant_data = RestaurantCreate.model_validate(payload)
    return await _create(
        restaurant_data,
        cover_image_file=cover_file,
        menu_source_file=menu_source_file,
        gallery_files=gallery_ordered,
        menu_item_files=menu_item_files,
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
