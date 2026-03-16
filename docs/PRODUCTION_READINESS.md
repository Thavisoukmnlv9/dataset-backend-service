# Production Readiness Checklist

Use this checklist before deploying **kanom-backend-service** to production.

## Environment variables (must set in production)

- **JWT_SECRET** – Strong random value (e.g. 32+ bytes). Never use `dev-secret-key-change-in-production` or leave empty.
- **DATABASE_URL** – PostgreSQL connection string for production DB.
- **ENVIRONMENT** – Set to `production` so CORS, error responses, and validation behave correctly.
- **CORS_ORIGINS** – Explicit list of allowed origins. Do not use `["*"]` in production.
- **GEMINI_API_KEY** – Required only if using embeddings/search; otherwise leave empty.
- **REDIS_URL** – For ARQ worker (email, background jobs). Required if using auth email flows.
- **Storage** – Either `STORAGE_PROVIDER=local` with safe `STORAGE_LOCAL_BASE_DIR` or configure MinIO/S3 with secure credentials (no default `minioadmin`/`minioadmin123`).
- **MAIL_*** (Brevo)** – Set if using email verification or password reset.

Reference: `.env.example` (do not commit `.env` or real secrets).

## Infra / deployment

- **start.sh** – Set `APP_DIR` (and optionally `VENV_PATH`) for your deployment root. Script runs `prisma generate` and `pip install -r requirements/prod.txt` from that directory.
- **Worker** – Run the ARQ worker separately (e.g. `./worker.sh` or `python -m app.worker`) on a process that has access to the same Redis and `.env` as the API.
- **Health** – `/health` and `/api/v1/health` are available; consider adding a DB ping to health if you need readiness checks.

## Security (already applied in codebase)

- Sensitive headers (e.g. Authorization, Cookie) are redacted in error responses.
- In production, 500 error responses do not include request URL/path/params in the payload.
- CORS wildcard is disabled in production; explicit origins are required.
- Sanitization middleware is enabled for input hardening.

## Verification commands (local)

```bash
# From project root
make install
make generate
make test
uvicorn app.main:app --host 0.0.0.0 --port 8000
# In another terminal:
./worker.sh
```

Then: `curl -s http://localhost:8000/health` and run through critical auth/API flows.
