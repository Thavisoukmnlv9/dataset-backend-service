"""MinIO storage adapter - wraps existing MinIOService."""

from typing import Dict, List, Optional

from app.shared.schemas.base import ResponseModel
from app.shared.services.infrastructure.storage.port import StoragePort


class MinioStorageAdapter(StoragePort):
    """Adapter that delegates to the existing MinIOService (MinIO SDK)."""

    def __init__(self) -> None:
        # Lazy import to avoid circular import (file_service does not import storage)
        from app.shared.services.infrastructure.file_service import MinIOService
        self._minio = MinIOService()

    async def upload_file(
        self,
        file,
        folder: str = "files",
        auto_resize: bool = True,
    ) -> ResponseModel:
        return await self._minio.upload_file(file, folder=folder, auto_resize=auto_resize)

    async def delete_file(self, object_name: str) -> ResponseModel:
        return await self._minio.delete_file(object_name)

    async def move_delete_file(
        self,
        object_name: str,
        folder: str = "deleted_files",
    ) -> ResponseModel:
        return await self._minio.move_delete_file(object_name, folder=folder)

    def extract_object_name_from_url(self, url_or_object_name: str) -> Optional[str]:
        return self._minio.extract_object_name_from_url(url_or_object_name or "")

    async def get_presigned_url(
        self,
        object_name: str,
        expires_in: int = 86400,
    ) -> Optional[str]:
        hours = max(1, expires_in // 3600)
        return await self._minio.get_file_url(object_name, expires_in_hours=hours)

    async def get_presigned_urls_for_file(
        self,
        image_urls: List[str],
        expires_in_hours: int = 24,
    ) -> List[Optional[str]]:
        return await self._minio.get_presigned_urls_for_file(
            image_urls, expires_in_hours=expires_in_hours
        )

    async def get_resized_image_urls(
        self,
        original_url: str,
        expires_in_hours: int = 24,
    ) -> Dict[str, Optional[str]]:
        return await self._minio.get_resized_image_urls(
            original_url, expires_in_hours=expires_in_hours
        )

    async def upload_multiple_image(
        self,
        files: List,
        folder: str = "files",
        auto_resize: bool = True,
    ) -> ResponseModel:
        return await self._minio.upload_multiple_image(
            files, folder=folder, auto_resize=auto_resize
        )

    async def upload_multiple_video(
        self,
        files: List,
        folder: str = "files",
    ) -> ResponseModel:
        return await self._minio.upload_multiple_video(files, folder=folder)
