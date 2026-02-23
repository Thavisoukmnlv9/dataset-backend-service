"""Storage provider factory - resolves adapter from config."""

import logging
from typing import Optional

from app.core.config import settings
from app.shared.services.infrastructure.storage.port import StoragePort

logger = logging.getLogger(__name__)

_ADAPTER: Optional[StoragePort] = None


def _validate_remote_config() -> None:
    """Validate required env for remote providers (minio, s3, wasabi)."""
    provider = (settings.storage_provider or "local").strip().lower()
    if provider == "local":
        return
    # MinIO can use STORAGE_* or legacy MINIO_*
    if provider == "minio":
        if not (settings.storage_endpoint or settings.minio_endpoint):
            raise ValueError(
                "STORAGE_PROVIDER=minio requires STORAGE_ENDPOINT or MINIO_ENDPOINT"
            )
        return
    if provider in ("s3", "wasabi"):
        if not (settings.storage_access_key or settings.minio_access_key):
            raise ValueError(
                f"STORAGE_PROVIDER={provider} requires STORAGE_ACCESS_KEY or MINIO_ACCESS_KEY"
            )
        if not (settings.storage_secret_key or settings.minio_secret_key):
            raise ValueError(
                f"STORAGE_PROVIDER={provider} requires STORAGE_SECRET_KEY or MINIO_SECRET_KEY"
            )
        if not settings.storage_bucket:
            raise ValueError(f"STORAGE_PROVIDER={provider} requires STORAGE_BUCKET")


def get_storage_adapter() -> StoragePort:
    """Resolve and return the configured storage adapter. Cached per process."""
    global _ADAPTER
    if _ADAPTER is not None:
        return _ADAPTER

    provider = (settings.storage_provider or "local").strip().lower()
    _validate_remote_config()

    if provider == "local":
        from app.shared.services.infrastructure.storage.adapters.local import (
            LocalStorageAdapter,
        )
        _ADAPTER = LocalStorageAdapter()
        logger.info("Storage adapter: local filesystem (%s)", settings.storage_local_base_dir)
    elif provider == "minio":
        from app.shared.services.infrastructure.storage.adapters.minio import (
            MinioStorageAdapter,
        )
        _ADAPTER = MinioStorageAdapter()
        logger.info("Storage adapter: MinIO")
    elif provider == "wasabi":
        from app.shared.services.infrastructure.storage.adapters.s3 import (
            WasabiStorageAdapter,
        )
        _ADAPTER = WasabiStorageAdapter()
        logger.info("Storage adapter: Wasabi (S3-compatible)")
    elif provider == "s3":
        from app.shared.services.infrastructure.storage.adapters.s3 import (
            S3StorageAdapter,
        )
        _ADAPTER = S3StorageAdapter()
        logger.info("Storage adapter: AWS S3")
    else:
        raise ValueError(
            f"Unknown STORAGE_PROVIDER={provider}. Use: local, minio, s3, wasabi"
        )

    return _ADAPTER


def reset_storage_adapter() -> None:
    """Clear cached adapter (for tests or config reload)."""
    global _ADAPTER
    _ADAPTER = None


# Facade used by application code
storage_service: StoragePort = get_storage_adapter()
