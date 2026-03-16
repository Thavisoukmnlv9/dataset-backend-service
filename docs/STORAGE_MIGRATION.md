# Storage: Port & Adapter (Hexagonal) Migration

## Summary

File storage is now abstracted behind a **Storage Port** with pluggable adapters. You can switch providers via configuration without changing business logic.

- **Default**: `local` (project filesystem) for dev/local.
- **Remote**: `minio`, `s3`, `wasabi`.

## New environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STORAGE_PROVIDER` | `local` | One of: `local`, `minio`, `s3`, `wasabi` |
| **Local (when provider=local)** | | |
| `STORAGE_LOCAL_BASE_DIR` | `uploads` | Directory for saved files (relative to app root) |
| `STORAGE_LOCAL_PUBLIC_BASE_URL` | `/uploads` | URL prefix for served files (e.g. `/uploads`) |
| **Remote (minio / s3 / wasabi)** | | |
| `STORAGE_BUCKET` | `kanom-media` | Bucket name |
| `STORAGE_REGION` | (none) | Region (S3/Wasabi) |
| `STORAGE_ENDPOINT` | (none) | Custom endpoint (MinIO/Wasabi; e.g. `minio:9000`, `s3.wasabisys.com`) |
| `STORAGE_ACCESS_KEY` | (none) | Access key (or use `MINIO_ACCESS_KEY` for MinIO) |
| `STORAGE_SECRET_KEY` | (none) | Secret key (or use `MINIO_SECRET_KEY` for MinIO) |
| `STORAGE_USE_SSL` | `false` | Use HTTPS for endpoint |
| `STORAGE_PRESIGN_EXPIRES_SECONDS` | `86400` | Presigned URL expiry (24h) |
| `STORAGE_PUBLIC_BASE_URL` | (none) | Optional public CDN/base URL for objects |

## Default behaviour

- **Provider**: `local` if `STORAGE_PROVIDER` is unset.
- **Local**: Files are stored under `STORAGE_LOCAL_BASE_DIR` (e.g. `uploads/users/...`). The app mounts this at `STORAGE_LOCAL_PUBLIC_BASE_URL` so URLs like `/uploads/users/xxx.jpg` work. No MinIO or S3 required.

## Switching providers

### Local (default)

No extra env; works out of the box.

```bash
# Optional, already the default
STORAGE_PROVIDER=local
```

### MinIO

Use existing MinIO env vars (or the new ones). MinIO adapter still uses `MINIO_*` if `STORAGE_*` are not set.

```bash
STORAGE_PROVIDER=minio
# Either:
STORAGE_ENDPOINT=localhost:9000
STORAGE_ACCESS_KEY=minioadmin
STORAGE_SECRET_KEY=minioadmin123
# Or keep using:
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
```

### Wasabi (S3-compatible)

```bash
STORAGE_PROVIDER=wasabi
STORAGE_BUCKET=your-bucket
STORAGE_REGION=us-east-1
STORAGE_ENDPOINT=s3.wasabisys.com
STORAGE_ACCESS_KEY=...
STORAGE_SECRET_KEY=...
STORAGE_USE_SSL=true
```

### AWS S3

```bash
STORAGE_PROVIDER=s3
STORAGE_BUCKET=your-bucket
STORAGE_REGION=us-east-1
STORAGE_ACCESS_KEY=...
STORAGE_SECRET_KEY=...
# Do not set STORAGE_ENDPOINT (uses AWS default)
```

## Code usage

Use the storage facade everywhere (no provider-specific imports):

```python
from app.shared.services.infrastructure.storage import storage_service

# Same API as before
result = await storage_service.upload_file(avatar_file, "users")
object_name = storage_service.extract_object_name_from_url(url)
urls = await storage_service.get_presigned_urls_for_file([object_name])
await storage_service.move_delete_file(old_path, "deleted-users")
resized = await storage_service.get_resized_image_urls(user.avatar_url)
```

- **Local**: “Presigned” URLs are normal static URLs (e.g. `/uploads/users/xxx.jpg`).
- **MinIO**: Keeps current behaviour (resized images, presigned URLs).
- **S3/Wasabi**: Presigned URLs; resized variants return the same URL (no server-side resize).

## Backward compatibility

- `minio_service` in `file_service` remains for legacy scripts; it is a lazy proxy to `MinIOService`. Prefer `storage_service` for all app code.
- Existing `ResponseModel` shape (`success`, `data`, `message`) and method signatures are unchanged.

## Validation

If you set `STORAGE_PROVIDER=minio|s3|wasabi` and omit required credentials or bucket, the app will fail at startup with a clear error (e.g. missing `STORAGE_ACCESS_KEY`).

## Tests

Basic storage tests (factory + local adapter) are in `tests/test_storage.py`. Run with:

```bash
pytest tests/test_storage.py -v
```

(Requires `pytest` and `pytest-asyncio` if not already in your env.)
