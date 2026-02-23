# Reflector Catalog — dataset Tourism Middleware API

> Auto-generated catalog describing every module, file, public class/function, and call relationships.
> Last updated: 2026-02-23 (post-refactor)

---

## Architecture Overview

```
Entrypoint (app/main.py → create_app)
  ├── Middleware (core/middleware.py)
  ├── Exception handlers (core/exceptions.py)
  ├── Service loader (core/urls.py → register_services)
  │   ├── Auth module  → /api/v1/auth/*
  │   └── Users module → /api/v1/users/*
  └── Core routes (/, /health, /api/v1/health)

Flow per request:
  HTTP → Middleware → Route (api/routes.py) → Service → Prisma ORM → PostgreSQL
```

---

## 1. Entrypoint & App Factory

### `app/main.py`
| Item | Description |
|------|-------------|
| **Purpose** | FastAPI application factory and lifespan manager |
| `create_app()` | Creates FastAPI instance, registers middleware, exception handlers, static files, and services |
| `lifespan()` | Async context manager handling DB connect on startup, cleanup on shutdown |
| `app` | Module-level app instance (`app = create_app()`) — used by uvicorn |
| **Called by** | `uvicorn app.main:app`, Docker entrypoint |

### `app/worker.py`
| Item | Description |
|------|-------------|
| **Purpose** | ARQ background worker entrypoint |
| **Called by** | `python -m app.worker`, Makefile `run-worker` |

---

## 2. Core Package (`app/core/`)

### `config.py`
| Item | Description |
|------|-------------|
| **Purpose** | Centralised environment-based configuration |
| `Settings` (class) | Pydantic `BaseSettings` with all env vars: DB, JWT, CORS, email, storage, Redis |
| `settings` | Singleton instance, loaded at import time |
| `validate_production_secrets()` | Raises on insecure defaults in production |
| **Called by** | Nearly every module that needs configuration |

### `settings.py`
| Item | Description |
|------|-------------|
| **Purpose** | App metadata and service registry |
| `AppSettings` | API title, version, contact, license |
| `ServiceConfig` | Defines a loadable service module (name, import_path, router_name) |
| `SERVICES_TO_LOAD` | List of enabled services: Auth, Users |
| `API_ENDPOINTS` | Dict of endpoint prefix mappings |
| **Called by** | `urls.py`, `main.py` |

### `urls.py`
| Item | Description |
|------|-------------|
| **Purpose** | Dynamic service registration with allowlist |
| `load_service(app, name, path)` | Imports a module and registers its `router` on the app |
| `register_services(app)` | Iterates `SERVICES_TO_LOAD`, returns loaded/failed lists |
| `register_core_routes(app)` | Registers `/`, `/health`, `/api/v1/health` |
| **Called by** | `main.py → create_app()` |

### `middleware.py`
| Item | Description |
|------|-------------|
| **Purpose** | Middleware stack configuration |
| `setup_middleware(app)` | Registers RequestContext → SecurityHeaders → CORS → Sanitization middleware |
| **Called by** | `main.py → create_app()` |

### `exceptions.py`
| Item | Description |
|------|-------------|
| **Purpose** | Centralised exception handlers |
| `validation_exception_handler` | Handles Pydantic `RequestValidationError` → 422 |
| `http_exception_handler` | Handles `HTTPException` and `StandardHTTPException` → structured JSON |
| `general_exception_handler` | Catches unhandled exceptions → 500 (no stack trace leak) |
| `setup_exception_handlers(app)` | Registers all handlers |
| **Called by** | `main.py → create_app()` |

### `security.py`
| Item | Description |
|------|-------------|
| **Purpose** | JWT creation/verification, password hashing, token management |
| `hash_password(pw)` | BCrypt hash with SHA-256 pre-hash (handles >72-byte passwords) |
| `verify_password(plain, hashed)` | Verify password against hash |
| `hash_token(token)` | SHA-256 hash for storing tokens in DB |
| `create_access_token(data)` | JWT access token |
| `create_refresh_token(data)` | JWT refresh token |
| `create_and_store_refresh_token(user_id)` | Creates + persists refresh token in DB |
| `verify_and_revoke_refresh_token(token)` | One-time-use verify + delete |
| `verify_token(token)` | Decode + verify JWT |
| `validate_password_strength(pw)` | Min 8 chars, upper, lower, digit |
| `create_email_verification_token(data)` | JWT for email verification |
| `verify_email_verification_token(token)` | Verify email verification JWT |
| **Called by** | Auth services, dependencies.py |

### `redis_client.py`
| Item | Description |
|------|-------------|
| **Purpose** | Redis async client singleton |
| `get_redis()` | Returns cached `redis.asyncio.Redis` instance |
| **Called by** | `worker.py`, rate limit service |

### `request_context.py`
| Item | Description |
|------|-------------|
| **Purpose** | ASGI middleware adding `X-Request-ID` header and timing |
| `RequestContextMiddleware` | Generates UUID per request, logs duration |
| **Called by** | `middleware.py` |

### `security_middleware.py`
| Item | Description |
|------|-------------|
| **Purpose** | ASGI middleware adding security headers |
| `SecurityHeadersMiddleware` | Adds `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`, HSTS |
| **Called by** | `middleware.py` |

### `worker.py`
| Item | Description |
|------|-------------|
| **Purpose** | ARQ background task definitions |
| `send_verification_email_task` | Worker task wrapping `mail_service.send_verification_email` |
| `send_password_reset_otp_email_task` | Worker task wrapping `mail_service.send_password_reset_otp_email` |
| `enqueue_verification_email(email, otp)` | Enqueue a verification email job |
| `enqueue_password_reset_otp_email(email, otp)` | Enqueue a password reset email job |
| `WorkerSettings` | ARQ worker configuration |
| **Called by** | `register.py`, `reset_password_service.py` |

### `startup.py`
| Item | Description |
|------|-------------|
| **Purpose** | Beautiful CLI startup display with ASCII art |
| `StartupDisplay` | Renders server info, environment, loaded services |
| **Called by** | `main.py → lifespan()` |

### `cli_display.py`
| Item | Description |
|------|-------------|
| **Purpose** | Constants for CLI display (icons, colors, ASCII art) |
| **Called by** | `startup.py` |

### `infrastructure_urls.py`
| Item | Description |
|------|-------------|
| **Purpose** | Infrastructure URL resolution |
| `get_infrastructure_urls()` | Returns dict of all service URLs from settings |
| `get_service_url(name)` | Get a specific service URL |
| **Called by** | `startup.py` |

---

## 3. Auth Module (`app/modules/auth/`)

### `api/routes.py`
| Item | Description |
|------|-------------|
| **Purpose** | Auth API router — thin controller layer |
| `router` | `APIRouter(prefix="/auth")` — 18 endpoints |
| **Endpoints** | `POST register, verify-email, resend-otp, login, vendor/login, logout, logout/device, revoke-all, refresh, vendor/refresh, forgot-password, verify-reset-otp, reset-password, admin/change-password, setup/verify-token, setup/password` `GET session, devices` `DELETE devices/{id}` |
| **Called by** | `urls.py → load_service()` |

### `services/login.py`
| Item | Description |
|------|-------------|
| **Purpose** | Email/password authentication |
| `EmailLoginService.authenticate_user(email, pw, request)` | Verifies credentials, creates tokens, session, device token |
| `login_user_email(user_data, request)` | Wrapper that maps service result to HTTP response |
| **Called by** | `routes.py → POST /auth/login` |

### `services/vendor_login.py`
| Item | Description |
|------|-------------|
| **Purpose** | Vendor-specific login with vendor role/status validation |
| `VendorLoginService.authenticate_vendor(email, pw, request)` | Like login but validates vendor role, includes vendor/RBAC data |
| `login_vendor_email(user_data, request)` | Wrapper |
| **Called by** | `routes.py → POST /auth/vendor/login` |
| **Note** | ~70% duplicated with `login.py` — candidate for future merge |

### `services/register.py`
| Item | Description |
|------|-------------|
| **Purpose** | User registration and email verification |
| `register_user(user_data)` | Creates user, generates OTP, queues verification email |
| `resend_verification_email(email)` | Resends OTP with throttle check |
| `verify_email_otp(email, otp)` | Verifies OTP and marks email as verified |
| **Called by** | `routes.py → POST /auth/register, verify-email, resend-otp` |

### `services/refresh.py`
| Item | Description |
|------|-------------|
| **Purpose** | Access token refresh |
| `RefreshTokenService.refresh_access_token(token, request)` | Verifies + revokes old refresh token, issues new pair |
| `refresh_token_endpoint(data, request)` | Wrapper |
| **Called by** | `routes.py → POST /auth/refresh` |

### `services/vendor_refresh.py`
| Item | Description |
|------|-------------|
| **Purpose** | Vendor-specific token refresh with RBAC data |
| `VendorRefreshTokenService.refresh_vendor_access_token(token, request)` | Like refresh but includes vendor data |
| `refresh_vendor_token_endpoint(data, request)` | Wrapper |
| **Called by** | `routes.py → POST /auth/vendor/refresh` |
| **Note** | ~80% duplicated with `refresh.py` — candidate for future merge |

### `services/logout.py`
| Item | Description |
|------|-------------|
| **Purpose** | User logout and session revocation |
| `LogoutService.logout_user(user_id, request)` | Revokes all tokens + sessions for user |
| `LogoutService.logout_user_from_device(user_id, device_info)` | Deactivates specific session |
| `LogoutService.revoke_all_user_sessions(user_id)` | Admin function to revoke all |
| **Called by** | `routes.py → POST /auth/logout, logout/device, revoke-all` |

### `services/get_session.py`
| Item | Description |
|------|-------------|
| **Purpose** | Session data retrieval |
| `get_session(user_id)` | Returns user data, active session, and RBAC permissions |
| **Called by** | `routes.py → GET /auth/session` |

### `services/otp_service_enhanced.py`
| Item | Description |
|------|-------------|
| **Purpose** | OTP generation, storage, verification with hashing |
| `EnhancedOTPService.generate_otp()` | Generates 6-digit OTP using `secrets` (cryptographically secure) |
| `EnhancedOTPService.upsert_otp(email, otp, purpose)` | Stores hashed OTP in DB |
| `EnhancedOTPService.verify_otp(email, otp, purpose)` | Verifies with attempt tracking |
| `EnhancedOTPService.can_resend_otp(email, purpose)` | Throttle check (60s) |
| **Called by** | `register.py`, `reset_password_service.py` |

### `services/mail_service.py`
| Item | Description |
|------|-------------|
| **Purpose** | Email sending via Brevo API + SMTP fallback |
| `send_verification_email(to, otp)` | Sends verification OTP email |
| `send_password_reset_otp_email(to, otp)` | Sends password reset OTP email |
| **Called by** | `worker.py` tasks |

### `services/reset_password_service.py`
| Item | Description |
|------|-------------|
| **Purpose** | Forgot password → OTP → reset token → new password flow |
| `ResetPasswordService.forgot_password(email, ip)` | Sends OTP for password reset |
| `ResetPasswordService.verify_otp(email, otp, ip)` | Verifies OTP, issues JWT reset token |
| `ResetPasswordService.reset_password(token, pw, ip)` | Sets new password, revokes sessions |
| `ResetPasswordService.admin_change_user_password(user_id, pw, admin_id)` | Admin password change |
| **Called by** | `routes.py → POST /auth/forgot-password, verify-reset-otp, reset-password, admin/change-password` |

### `services/password_setup_service.py`
| Item | Description |
|------|-------------|
| **Purpose** | Vendor onboarding password setup via JWT tokens |
| `PasswordSetupService.generate_setup_token(user_id)` | Creates setup JWT |
| `PasswordSetupService.verify_setup_token(token)` | Verifies setup JWT, returns user info |
| `PasswordSetupService.setup_password(token, pw)` | Sets password via setup token |
| **Called by** | `routes.py → POST /auth/setup/verify-token, setup/password` |

### `services/rate_limit_service.py`
| Item | Description |
|------|-------------|
| **Purpose** | Database-backed rate limiting |
| `RateLimitService.check_rate_limit(identifier, endpoint, ip)` | Checks/increments rate limit |
| `RateLimitService.get_identifier(ip, email)` | Generates rate limit identifier |
| **Called by** | `reset_password_service.py` |

### Schemas (`schemas/`)
| File | Key Models |
|------|-----------|
| `auth.py` | `UserCreate`, `UserLogin`, `TokenResponse`, `RefreshTokenRequest`, `ForgotPasswordRequest`, `ResetPasswordRequest`, `AdminChangePasswordRequest`, `EmailOTPVerificationRequest`, `ResendOTPRequest` |
| `user_create.py` | `UserCreate` (registration-specific variant) |
| `reset_password.py` | `VerifyOTPRequest`, `VerifyOTPResponse`, `ResetPasswordRequest` (reset-specific) |
| `password_setup.py` | `VerifySetupTokenRequest`, `SetupPasswordRequest` |
| `rbac.py` | `BusinessCreate`, `RbacRoleCreate`, `RbacUserRoleAssign` |

---

## 4. Users Module (`app/modules/users/`)

### `api/routes.py`
| Item | Description |
|------|-------------|
| **Purpose** | Users API router — thin controller layer |
| `router` | `APIRouter(prefix="/users")` — 13 endpoints |
| **Endpoints** | `GET stats, lookup, lookup/{id}, list, search, {id}` `POST create, {id}/restore` `PUT {id}, {id}/ban, {id}/verify-email, {id}/verify-phone` `DELETE {id}, {id}/hard` |
| **Called by** | `urls.py → load_service()` |

### `services/create.py`
| Item | Description |
|------|-------------|
| **Purpose** | User creation with image upload and RBAC roles |
| `create_user_with_form_data_and_image(data, avatar, admin_id)` | Transactional user + role creation |
| **Called by** | `routes.py → POST /users` |

### `services/get_list.py`
| Item | Description |
|------|-------------|
| **Purpose** | User listing with filtering, search, pagination, sorting |
| `get_users(filters, pagination, search, sort_json, filters_json)` | Main list endpoint |
| `search_users(query, filters, offset, limit)` | Search endpoint |
| **Called by** | `routes.py → GET /users, /users/search` |

### `services/get_one.py`
| Item | Description |
|------|-------------|
| **Purpose** | Single user retrieval with all relations |
| `get_user(user_id)` | Returns user with profile, roles, sessions |
| **Called by** | `routes.py → GET /users/{id}` |

### `services/update.py`
| Item | Description |
|------|-------------|
| **Purpose** | User updates, ban/unban, email/phone verification |
| `update_user(user_id, data, avatar)` | General user update |
| `ban_user(user_id, ban_data)` | Ban/unban |
| `verify_user_email(user_id)` | Admin email verification |
| `verify_user_phone(user_id)` | Admin phone verification |
| **Called by** | `routes.py → PUT /users/{id}/*` |

### `services/delete.py`
| Item | Description |
|------|-------------|
| **Purpose** | Soft delete, restore, and hard delete |
| `delete_user(user_id)` | Soft delete (sets `deleted_at`) |
| `restore_user(user_id)` | Restore (clears `deleted_at`) |
| `hard_delete_user(user_id)` | Permanent delete (cascades) |
| **Called by** | `routes.py → DELETE /users/{id}, POST /users/{id}/restore, DELETE /users/{id}/hard` |

### `services/stats.py`
| Item | Description |
|------|-------------|
| **Purpose** | User statistics and analytics dashboard |
| `get_user_stats()` | Returns total, active, banned, verified counts, role distribution, daily registrations |
| **Called by** | `routes.py → GET /users/stats` |

### `services/lookup.py`
| Item | Description |
|------|-------------|
| **Purpose** | User lookup for dropdowns and selectors |
| `lookup_users(query)` | Search users by name/email, returns id + display name |
| `lookup_user_by_id(user_id)` | Single user lookup |
| **Called by** | `routes.py → GET /users/lookup, /users/lookup/{id}` |

---

## 5. Shared Package (`app/shared/`)

### `exceptions.py`
| Item | Description |
|------|-------------|
| `StandardHTTPException` | Custom `HTTPException` with `error_code` and `fields` for structured errors |
| `raise_validation_error()` | 422 — validation error |
| `raise_not_found_error()` | 404 — resource not found |
| `raise_conflict_error()` | 409 — resource conflict |
| `raise_unauthorized_error()` | 401 — authentication required |
| `raise_forbidden_error()` | 403 — insufficient permissions |
| `raise_business_logic_error()` | Custom code — business logic error |

### `schemas/base.py`
| Item | Description |
|------|-------------|
| `ResponseModel` | Standard success envelope: `{success, data, message, timestamp, request_id}` |
| `ErrorResponse` | Standard error envelope: `{success, error, timestamp, request_id}` |
| `PaginationParams` | `page`, `limit`, `sort`, `order` + computed `skip`/`offset` |
| `PaginationResponse` | `page`, `limit`, `total`, `pages`, `has_next`, `has_prev` |
| `BaseEntity` | Base model with `id`, `created_at`, `updated_at`, `deleted_at` |

### `schemas/error.py`
| Item | Description |
|------|-------------|
| `StandardErrorResponse` | Full error response with `ErrorData` + `MetaData` |
| `ErrorField` | Field-level error detail |
| `ErrorData` | Error code, message, status_code, fields |
| `MetaData` | Request metadata (path, method, headers, params) |

### `utils/responses/response.py`
| Item | Description |
|------|-------------|
| `create_success_response(data, message)` | Creates `ResponseModel` |
| `create_error_response(code, message)` | Creates `ErrorResponse` |
| `create_pagination_response(items, total, page, limit, offset)` | Creates pagination metadata |
| `create_list_response(items, total, page, limit, offset)` | Success + pagination |

### `utils/responses/error_response.py`
| Item | Description |
|------|-------------|
| `create_standard_error_response(...)` | Full structured error |
| `create_validation_error_response(errors)` | Pydantic validation → structured error |
| `create_http_error_response(status, message)` | HTTP error → structured error |

### `services/infrastructure/storage/`
| Item | Description |
|------|-------------|
| `StoragePort` (ABC) | Hexagonal port: `upload_file`, `get_presigned_url`, `delete_file`, etc. |
| `get_storage_adapter()` | Factory returning LocalStorage, MinIO, S3, or Wasabi adapter |
| `storage_service` | Module-level singleton adapter instance |
| **Adapters** | `LocalStorageAdapter`, `MinioStorageAdapter`, `S3StorageAdapter`, `WasabiStorageAdapter` |

### `services/image_upload_service.py`
| Item | Description |
|------|-------------|
| `upload_image_with_cleanup(file, folder)` | Upload + old file cleanup |
| `upload_multiple_images_with_cleanup(files, folder)` | Batch upload |

### `middleware/sanitization_middleware.py`
| Item | Description |
|------|-------------|
| `SanitizationMiddleware` | Sanitizes query params (body sanitization disabled to avoid breaking JSON) |

---

## 6. API Dependencies (`app/api/dependencies.py`)

| Item | Description |
|------|-------------|
| `get_current_user(token)` | Decodes JWT, fetches user from DB |
| `get_current_active_user(user)` | Validates user is active + has valid session |
| `get_admin_user(user)` | Requires ADMIN or SUPER_ADMIN role |
| `get_super_admin_user(user)` | Requires SUPER_ADMIN role |
| `get_vendor_user(user)` | Requires vendor role |
| `get_database()` | Returns Prisma client |

---

## 7. Database (`app/prisma/`)

### `client.py`
| Item | Description |
|------|-------------|
| `prisma` | Singleton Prisma client instance |
| `connect_db()` | Startup connection |
| `cleanup_all_connections()` | Shutdown cleanup |
| `ensure_connection()` | Lazy reconnect |
| `get_db()` | FastAPI dependency |
| `health_check()` | DB health check (user.count) |

### `prisma/schema.prisma`
| Model | Description |
|-------|-------------|
| `User` | User accounts with profile, social login, security fields |
| `Session` | Active sessions with device info, fingerprint, trust level |
| `RefreshToken` | Hashed refresh tokens with revocation tracking |
| `ApiKey` | API key management |
| `RateLimit` | Database-backed rate limiting |

---

## 8. Possibly Used Indirectly (DO NOT DELETE)

| File | Reason to Keep |
|------|----------------|
| `app/core/cli_display.py` | Used by `startup.py` for ASCII art constants |
| `app/core/infrastructure_urls.py` | Used by `startup.py` for infrastructure URL display |
| `app/shared/utils/database/transactions.py` | Transaction utilities — not currently used but provides `TransactionManager` for future use |
| `app/shared/utils/database/filter_builder.py` | Generic filter builder — not adopted by `get_list.py` yet but useful for future modules |
| `app/shared/utils/validation/sanitization.py` | Sanitization utilities — used by `SanitizationMiddleware` |
| `app/shared/services/infrastructure/file_service.py` | MinIO service — used by `MinioStorageAdapter` |
| `app/modules/auth/schemas/rbac.py` | RBAC schemas — used by `get_session.py` and `create.py` indirectly via RBAC data |
| `seed/seed_users_auth_data.py` | Database seeding script — used by `seed.sh` |

---

## 9. Known Technical Debt

| Item | Severity | Notes |
|------|----------|-------|
| `vendor_login.py` duplicates `login.py` (~70%) | Medium | Merge into single service with `is_vendor` flag |
| `vendor_refresh.py` duplicates `refresh.py` (~80%) | Medium | Same merge strategy |
| Password validation duplicated 6+ times | Low | Extract to `app/shared/utils/validation/password.py` |
| `get_list.py` user mapping duplicated with `get_one.py` | Medium | Extract shared user serializer |
| `stats.py` fetches all users to count by role | High (perf) | Use Prisma `groupBy` when available |
| `stats.py` makes 30 individual queries for daily stats | High (perf) | Use single query with `group_by` |
| `file_service.py` unbounded in-memory caches | Medium | Add TTL-based eviction |
| `worker.py` creates new Redis pool per enqueue call | Low | Reuse connection pool |
