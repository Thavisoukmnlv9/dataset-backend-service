"""S3-compatible storage adapter (AWS S3 and Wasabi) using boto3."""

import asyncio
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.shared.schemas.base import ResponseModel
from app.shared.services.infrastructure.storage.port import StoragePort

logger = logging.getLogger(__name__)


def _get_s3_client():
    """Create boto3 S3 client from settings. Used for both S3 and Wasabi."""
    import boto3
    from botocore.config import Config

    kwargs: Dict[str, Any] = {
        "service_name": "s3",
        "aws_access_key_id": settings.storage_access_key or settings.minio_access_key,
        "aws_secret_access_key": settings.storage_secret_key or settings.minio_secret_key,
        "region_name": settings.storage_region or "us-east-1",
        "config": Config(signature_version="s3v4"),
    }
    if settings.storage_endpoint:
        kwargs["endpoint_url"] = (
            f"https://{settings.storage_endpoint}"
            if settings.storage_use_ssl
            else f"http://{settings.storage_endpoint}"
        )
    return boto3.client(**kwargs)


class S3StorageAdapter(StoragePort):
    """
    S3-compatible storage (AWS S3 or Wasabi).
    Set STORAGE_ENDPOINT for Wasabi (e.g. s3.wasabisys.com); leave unset for AWS S3.
    """

    def __init__(self) -> None:
        self._bucket = settings.storage_bucket
        self._public_base = (
            settings.storage_public_base_url
            or settings.minio_public_url
            or ""
        ).rstrip("/")
        self._expires = settings.storage_presign_expires_seconds
        self._client = _get_s3_client()

    def _run_sync(self, fn, *args, **kwargs):
        return asyncio.get_event_loop().run_in_executor(
            None, lambda: fn(*args, **kwargs)
        )

    def _generate_object_name(self, file: UploadFile, folder: str = "files") -> str:
        ext = os.path.splitext(file.filename or "")[1]
        return f"{folder}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4()}{ext}"

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
        ct = file.content_type or "application/octet-stream"
        if ct not in set(settings.allowed_file_types):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type: {ct}",
            )

    async def upload_file(
        self,
        file: UploadFile,
        folder: str = "files",
        auto_resize: bool = True,
    ) -> ResponseModel:
        try:
            self._validate_file(file)
            object_name = self._generate_object_name(file, folder)
            content = await file.read()
            ct = file.content_type or "application/octet-stream"

            await self._run_sync(
                self._client.put_object,
                Bucket=self._bucket,
                Key=object_name,
                Body=content,
                ContentType=ct,
            )
            url = f"{self._public_base}/{self._bucket}/{object_name}" if self._public_base else object_name
            return ResponseModel(
                success=True,
                data={
                    "object_name": object_name,
                    "filename": file.filename,
                    "content_type": ct,
                    "size": len(content),
                    "url": url,
                    "uploaded_at": datetime.utcnow().isoformat(),
                },
                message="File uploaded successfully",
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("S3 upload failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Upload failed: {str(e)}",
            )

    async def delete_file(self, object_name: str) -> ResponseModel:
        try:
            await self._run_sync(
                self._client.delete_object,
                Bucket=self._bucket,
                Key=object_name,
            )
            return ResponseModel(
                success=True,
                data={"object_name": object_name, "deleted_at": datetime.utcnow().isoformat()},
                message="File deleted successfully",
            )
        except Exception as e:
            logger.exception("S3 delete failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Delete failed: {str(e)}",
            )

    async def move_delete_file(
        self,
        object_name: str,
        folder: str = "deleted_files",
    ) -> ResponseModel:
        try:
            filename = object_name.split("/")[-1]
            new_key = f"{folder}/{filename}"
            copy_src = {"Bucket": self._bucket, "Key": object_name}
            await self._run_sync(
                self._client.copy_object,
                CopySource=copy_src,
                Bucket=self._bucket,
                Key=new_key,
            )
            await self._run_sync(
                self._client.delete_object,
                Bucket=self._bucket,
                Key=object_name,
            )
            return ResponseModel(
                success=True,
                data={
                    "original_object_name": object_name,
                    "moved_to": new_key,
                    "moved_at": datetime.utcnow().isoformat(),
                },
                message="File moved to deleted folder successfully",
            )
        except Exception as e:
            err = getattr(e, "response", {}) or {}
            code = (err.get("Error") or {}).get("Code", "")
            if code in ("404", "NoSuchKey"):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File not found: {object_name}",
                )
            logger.exception("S3 move_delete failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Move delete failed: {str(e)}",
            )

    def extract_object_name_from_url(self, url_or_object_name: str) -> Optional[str]:
        if not url_or_object_name:
            return None
        s = (url_or_object_name or "").strip()
        if "?" in s:
            s = s.split("?")[0]
        if s.startswith("http://") or s.startswith("https://"):
            parsed = urlparse(s)
            path = parsed.path.lstrip("/")
            if f"{self._bucket}/" in path:
                return path.split(f"{self._bucket}/", 1)[-1]
            return path if path else None
        return s

    async def get_presigned_url(
        self,
        object_name: str,
        expires_in: int = 86400,
    ) -> Optional[str]:
        try:
            url = await self._run_sync(
                self._client.generate_presigned_url,
                "get_object",
                Params={"Bucket": self._bucket, "Key": object_name},
                ExpiresIn=min(expires_in, 604800),
            )
            return url
        except Exception as e:
            logger.warning("Presign failed for %s: %s", object_name, e)
            return None

    async def get_presigned_urls_for_file(
        self,
        image_urls: List[str],
        expires_in_hours: int = 24,
    ) -> List[Optional[str]]:
        expires = expires_in_hours * 3600
        result: List[Optional[str]] = []
        for url in image_urls:
            if not url:
                result.append(None)
                continue
            obj = self.extract_object_name_from_url(url)
            if obj and await self.file_exists(obj):
                u = await self.get_presigned_url(obj, expires_in=expires)
                result.append(u)
            else:
                result.append(None)
        return result

    async def file_exists(self, object_name: str) -> bool:
        try:
            await self._run_sync(
                self._client.head_object,
                Bucket=self._bucket,
                Key=object_name,
            )
            return True
        except Exception:
            return False


class WasabiStorageAdapter(S3StorageAdapter):
    """
    Wasabi is S3-compatible. Use STORAGE_PROVIDER=wasabi and set
    STORAGE_ENDPOINT (e.g. s3.wasabisys.com), STORAGE_REGION, credentials.
    """

    def __init__(self) -> None:
        super().__init__()
