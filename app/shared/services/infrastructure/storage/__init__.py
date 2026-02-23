"""Storage Port & Adapters (Hexagonal) - switchable file/object storage."""

from .factory import get_storage_adapter, storage_service
from .port import StoragePort

__all__ = [
    "StoragePort",
    "get_storage_adapter",
    "storage_service",
]
