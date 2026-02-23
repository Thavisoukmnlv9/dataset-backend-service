"""Basic tests for storage Port & Adapter (factory + local adapter)."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure app is on path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def mock_settings_local():
    """Force storage provider to local and use a temp dir."""
    with tempfile.TemporaryDirectory() as tmp:
        m = MagicMock()
        m.storage_provider = "local"
        m.storage_local_base_dir = tmp
        m.storage_local_public_base_url = "/uploads"
        m.max_file_size = 10 * 1024 * 1024
        m.allowed_file_types = ["image/jpeg", "image/png"]
        with patch("app.shared.services.infrastructure.storage.factory.settings", m), \
             patch("app.shared.services.infrastructure.storage.adapters.local.settings", m):
            yield m


@pytest.fixture
def reset_storage():
    """Reset the cached storage adapter so config changes take effect."""
    from app.shared.services.infrastructure.storage import factory
    factory.reset_storage_adapter()
    yield
    factory.reset_storage_adapter()


def test_factory_returns_local_adapter(mock_settings_local, reset_storage):
    """Factory returns LocalStorageAdapter when STORAGE_PROVIDER=local."""
    from app.shared.services.infrastructure.storage.factory import get_storage_adapter
    from app.shared.services.infrastructure.storage.adapters.local import LocalStorageAdapter

    adapter = get_storage_adapter()
    assert isinstance(adapter, LocalStorageAdapter)


def test_factory_raises_unknown_provider(reset_storage):
    """Factory raises ValueError for unknown STORAGE_PROVIDER."""
    from app.shared.services.infrastructure.storage import factory

    with patch.object(factory, "settings", MagicMock(storage_provider="unknown")):
        with pytest.raises(ValueError, match="Unknown STORAGE_PROVIDER"):
            factory.get_storage_adapter()


def _make_upload_file(filename: str, content: bytes, content_type: str = "image/jpeg"):
    """Build a minimal UploadFile-like object for tests."""
    import io
    f = io.BytesIO(content)
    u = MagicMock()
    u.filename = filename
    u.file = f
    u.content_type = content_type
    u.size = len(content)
    async def _read():
        return content
    u.read = _read
    return u


@pytest.mark.asyncio
async def test_local_adapter_upload_and_extract(mock_settings_local, reset_storage):
    """Local adapter: upload file, then extract object name from URL."""
    from app.shared.services.infrastructure.storage.factory import get_storage_adapter

    adapter = get_storage_adapter()
    content = b"fake image content"
    f = _make_upload_file("test.jpg", content)

    result = await adapter.upload_file(f, folder="users")
    assert result.success is True
    assert result.data is not None
    object_name = result.data.get("object_name")
    url = result.data.get("url")
    assert object_name is not None
    assert "users/" in object_name
    assert url is not None

    extracted = adapter.extract_object_name_from_url(url)
    assert extracted == object_name
    extracted_from_name = adapter.extract_object_name_from_url(object_name)
    assert extracted_from_name == object_name


@pytest.mark.asyncio
async def test_local_adapter_presigned_is_public_url(mock_settings_local, reset_storage):
    """Local adapter: get_presigned_url returns public URL when file exists."""
    from app.shared.services.infrastructure.storage.factory import get_storage_adapter

    adapter = get_storage_adapter()
    f = _make_upload_file("presign.jpg", b"x")
    result = await adapter.upload_file(f, folder="test")
    object_name = result.data["object_name"]

    url = await adapter.get_presigned_url(object_name)
    assert url is not None
    assert object_name in url or url.endswith(object_name.lstrip("/"))
