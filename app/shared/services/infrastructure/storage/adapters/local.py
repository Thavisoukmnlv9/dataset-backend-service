"""Local filesystem storage adapter - default for dev/local."""

import logging
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.shared.schemas.base import ResponseModel
from app.shared.services.infrastructure.storage.port import StoragePort

logger = logging.getLogger(__name__)


class LocalStorageAdapter(StoragePort):
    """
    Store files on the local project filesystem.
    'Presigned' URLs are just public paths (e.g. /uploads/users/xxx.jpg).
    """

    def __init__(self) -> None:
        self._base_dir = Path(settings.storage_local_base_dir)
        self._public_base = (settings.storage_local_public_base_url or "/uploads").rstrip("/")
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _object_to_path(self, object_name: str) -> Path:
        """Convert object name to absolute filesystem path (no path traversal)."""
        parts = Path(object_name).parts
        safe = Path(*parts)
        resolved = (self._base_dir / safe).resolve()
        base_resolved = self._base_dir.resolve()
        if not str(resolved).startswith(str(base_resolved)):
            raise ValueError(f"Path outside base dir: {object_name}")
        return resolved

    def _generate_object_name(self, file: UploadFile, folder: str = "files") -> str:
        ext = os.path.splitext(file.filename or "")[1]
        unique_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{folder}/{timestamp}_{unique_id}{ext}"

    def _validate_file(self, file: UploadFile) -> None:
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No filename provided",
            )
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
        if size > settings.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Max: {settings.max_file_size} bytes",
            )
        allowed = set(settings.allowed_file_types)
        ct = file.content_type or "application/octet-stream"
        if ct not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type: {ct}. Allowed: {list(allowed)}",
            )

    async def upload_file(
        self,
        file: UploadFile,
        folder: str = "files",
        auto_resize: bool = True,
    ) -> ResponseModel:
        """Save file to local disk and return object_name and public URL."""
        try:
            self._validate_file(file)
            object_name = self._generate_object_name(file, folder)
            dest = self._object_to_path(object_name)
            dest.parent.mkdir(parents=True, exist_ok=True)

            with dest.open("wb") as f:
                content = await file.read()
                f.write(content)
            size = len(content)
            public_url = f"{self._public_base}/{object_name}"

            return ResponseModel(
                success=True,
                data={
                    "object_name": object_name,
                    "filename": file.filename,
                    "content_type": file.content_type or "application/octet-stream",
                    "size": size,
                    "url": public_url,
                    "uploaded_at": datetime.now(timezone.utc).isoformat(),
                },
                message="File uploaded successfully",
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Local upload failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Upload failed: {str(e)}",
            )

    async def delete_file(self, object_name: str) -> ResponseModel:
        """Delete file from local disk."""
        try:
            path = self._object_to_path(object_name)
            if not path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File not found: {object_name}",
                )
            path.unlink()
            return ResponseModel(
                success=True,
                data={"object_name": object_name, "deleted_at": datetime.now(timezone.utc).isoformat()},
                message="File deleted successfully",
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Local delete failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Delete failed: {str(e)}",
            )

    async def move_delete_file(
        self,
        object_name: str,
        folder: str = "deleted_files",
    ) -> ResponseModel:
        """Move file to a 'deleted' folder on disk."""
        try:
            src = self._object_to_path(object_name)
            if not src.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File not found: {object_name}",
                )
            filename = src.name
            new_object_name = f"{folder}/{filename}"
            dest = self._object_to_path(new_object_name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
            return ResponseModel(
                success=True,
                data={
                    "original_object_name": object_name,
                    "moved_to": new_object_name,
                    "moved_at": datetime.now(timezone.utc).isoformat(),
                },
                message="File moved to deleted folder successfully",
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Local move_delete failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Move delete failed: {str(e)}",
            )

    def extract_object_name_from_url(self, url_or_object_name: str) -> Optional[str]:
        """Extract object name from URL or return as-is if already a path."""
        if not url_or_object_name:
            return None
        s = url_or_object_name.strip()
        if "?" in s:
            s = s.split("?")[0]
        if s.startswith("http://") or s.startswith("https://"):
            # Strip domain and base path
            base = self._public_base
            if base in s:
                idx = s.find(base) + len(base)
                return s[idx:].lstrip("/")
            return None
        return s

    async def get_presigned_url(
        self,
        object_name: str,
        expires_in: int = 86400,
    ) -> Optional[str]:
        """For local storage, return public URL (no signing)."""
        if not object_name:
            return None
        if await self.file_exists(object_name):
            return f"{self._public_base}/{object_name.lstrip('/')}"
        return None

    async def get_presigned_urls_for_file(
        self,
        image_urls: List[str],
        expires_in_hours: int = 24,
    ) -> List[Optional[str]]:
        """Return list of public URLs for local files."""
        result: List[Optional[str]] = []
        for url in image_urls:
            if not url:
                result.append(None)
                continue
            obj = self.extract_object_name_from_url(url)
            if obj:
                u = await self.get_presigned_url(obj, expires_in=expires_in_hours * 3600)
                result.append(u)
            else:
                result.append(None)
        return result

    async def file_exists(self, object_name: str) -> bool:
        """Check if file exists on disk."""
        path = self._object_to_path(object_name)
        return path.is_file()
