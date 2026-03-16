"""Build full URLs for uploaded file paths (e.g. uploads/restaurants/menu_items/...)."""
from typing import Optional

from app.core.config import settings


def path_to_upload_url(path: Optional[str]) -> Optional[str]:
    if not path or not str(path).strip():
        return None
    s = str(path).strip()
    if s.startswith("http://") or s.startswith("https://"):
        return s
    base = (settings.api_url or "").rstrip("/")
    segment = s if s.startswith("/") else f"/{s}"
    return f"{base}{segment}" if base else segment
