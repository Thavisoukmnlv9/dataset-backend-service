"""Storage Port (interface) for file/object storage - Hexagonal Architecture."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from fastapi import UploadFile

from app.shared.schemas.base import ResponseModel


class StoragePort(ABC):
    """
    Port (interface) for file and object storage.
    Implementations: LocalStorageAdapter, MinioStorageAdapter, S3StorageAdapter.
    """

    @abstractmethod
    async def upload_file(
        self,
        file: UploadFile,
        folder: str = "files",
        auto_resize: bool = True,
    ) -> ResponseModel:
        """Upload a single file. Returns ResponseModel with data.object_name and data.url."""
        ...

    @abstractmethod
    async def delete_file(self, object_name: str) -> ResponseModel:
        """Delete a file by object name."""
        ...

    @abstractmethod
    async def move_delete_file(
        self,
        object_name: str,
        folder: str = "deleted_files",
    ) -> ResponseModel:
        """Move object to a 'deleted' folder (soft delete)."""
        ...

    @abstractmethod
    def extract_object_name_from_url(self, url_or_object_name: str) -> Optional[str]:
        """Extract object name from a full URL or return as-is if already an object name."""
        ...

    @abstractmethod
    async def get_presigned_url(
        self,
        object_name: str,
        expires_in: int = 86400,
    ) -> Optional[str]:
        """Get a presigned URL for the object. For local storage, returns public URL."""
        ...

    @abstractmethod
    async def get_presigned_urls_for_file(
        self,
        image_urls: List[str],
        expires_in_hours: int = 24,
    ) -> List[Optional[str]]:
        """Get presigned (or public) URLs for a list of URLs/object names. Returns list of URL or None."""
        ...

    async def file_exists(self, object_name: str) -> bool:
        """Check if object exists. Optional; default implementation may not be overridden."""
        return True  # Override in adapters that can check

    async def get_resized_image_urls(
        self,
        original_url: str,
        expires_in_hours: int = 24,
    ) -> Dict[str, Optional[str]]:
        """
        Get URLs for resized versions (thumbnail, small, medium, large).
        Local/S3 adapters may return same URL for all sizes if resizing not supported.
        """
        url = await self.get_presigned_url(
            self.extract_object_name_from_url(original_url) or original_url,
            expires_in=expires_in_hours * 3600,
        )
        if not url:
            return {}
        return {
            "thumbnail": url,
            "small": url,
            "medium": url,
            "large": url,
        }

    async def upload_multiple_image(
        self,
        files: List[UploadFile],
        folder: str = "files",
        auto_resize: bool = True,
    ) -> ResponseModel:
        """Upload multiple image files. Default: sequential upload_file."""
        from app.shared.schemas.base import ResponseModel as RM

        uploaded: List[Dict[str, Any]] = []
        for f in files:
            result = await self.upload_file(f, folder=folder, auto_resize=auto_resize)
            if result.success and result.data:
                uploaded.append(result.data)
        return RM(
            success=True,
            data={"files": uploaded, "count": len(uploaded)},
            message=f"Uploaded {len(uploaded)} files",
        )

    async def upload_multiple_video(
        self,
        files: List[UploadFile],
        folder: str = "files",
    ) -> ResponseModel:
        """Upload multiple video files. Default: upload_file_without_resize if available or upload_file."""
        from app.shared.schemas.base import ResponseModel as RM

        uploaded: List[Dict[str, Any]] = []
        for f in files:
            result = await self.upload_file(f, folder=folder, auto_resize=False)
            if result.success and result.data:
                uploaded.append(result.data)
        return RM(
            success=True,
            data={"files": uploaded, "count": len(uploaded)},
            message=f"Uploaded {len(uploaded)} video files",
        )
