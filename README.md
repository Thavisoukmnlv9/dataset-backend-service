# kanom Backend Service

FastAPI backend for the kanom tourism platform: auth, users, restaurants, cafes, bars, attractions, and souvenirs. Built with Prisma (PostgreSQL), optional Redis (ARQ worker), and configurable storage (local / MinIO / S3).

## Table of contents

- [Features](#-features)
- [Prerequisites](#-prerequisites)
- [Quick start](#-quick-start)
- [Configuration](#-configuration)
- [Running the app](#-running-the-app)
- [Testing](#-testing)
- [Project structure](#-project-structure)
- [API overview](#-api-overview)
- [Production](#-production)
- [Troubleshooting](#-troubleshooting)
- [Docs & contact](#-docs--contact)

---

## 🚀 Features

- **Auth** — Registration, login, JWT access/refresh, email verification, password reset
- **Users** — Profile and role management (RBAC)
- **Tourism modules** — Restaurants, cafes, bars, attractions, souvenirs (CRUD, gallery, translations)
- **Storage** — Local filesystem or MinIO/S3; image uploads with validation
- **Background jobs** — ARQ worker for verification and password-reset emails (Redis)
- **Security** — BCrypt password hashing, CORS, security headers, input sanitization
- **Health & docs** — `/health`, `/api/v1/health`, Swagger at `/docs`

---

## 📋 Prerequisites

- **Python 3.11+**
- **PostgreSQL**
- **Prisma CLI** (`npm i -g prisma` or use npx)
- **Redis** (required for the ARQ worker and email flows)

---

## ⚡ Quick start

From the **project root**:

```bash
# Clone and enter repo
git clone <repo-url>
cd kanom-backend-service

# Virtual env (recommended)
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install deps and generate Prisma client
make install
make generate

# Copy env and set at least DATABASE_URL and JWT_SECRET
cp .env.example .env
# edit .env

# Apply schema to DB
make migrate

# Optional: seed users/auth data
make seed
```

Then start the API and (in another terminal) the worker:

```bash
# Terminal 1
make run

# Terminal 2 — health check
curl -s http://localhost:8000/health

# Terminal 2 — worker (needs Redis)
./worker.sh
# or: make run-worker
```

---

## ⚙️ Configuration

Configuration is via environment variables. Use `.env` in the project root (never commit it).

- **Reference**: copy from `.env.example` and adjust.
- **Required**: `DATABASE_URL`, `JWT_SECRET` (use a strong random value in production).
- **Optional**: `REDIS_URL` (for worker), `GEMINI_API_KEY` (embeddings), storage (MinIO/S3), mail (Brevo), CORS, etc.

For a **production checklist** and required variables, see **[docs/PRODUCTION_READINESS.md](docs/PRODUCTION_READINESS.md)**.

---

## 🏃 Running the app

All commands from **project root** (where `Makefile` and `prisma/` live).

| Goal              | Command |
|-------------------|---------|
| API (dev, reload) | `make run` |
| API (one-off)     | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| Worker            | `./worker.sh` or `make run-worker` |
| DB push           | `make migrate` |
| Prisma generate   | `make generate` |
| Seed              | `make seed` |

Swagger UI: **http://localhost:8000/docs**

---

## 🧪 Testing

```bash
# All tests (from project root)
make test

# Exclude Qdrant tests if Qdrant is not running
pytest tests/ -v --tb=short --ignore=tests/test_restaurants_qdrant.py

# With coverage
make test-cov
```

---

## 📁 Project structure

```
kanom-backend-service/
├── app/
│   ├── core/           # Config, security, middleware, exceptions, URLs
│   ├── modules/        # Domain modules
│   │   ├── auth/       # Login, register, refresh, password reset
│   │   ├── users/      # User management
│   │   ├── restaurants/
│   │   ├── cafes/
│   │   ├── bars/
│   │   ├── attractions/
│   │   └── souvenirs/
│   ├── shared/        # Storage, schemas, utils, sanitization
│   ├── prisma/        # Generated client + connection helpers
│   ├── main.py        # FastAPI app entry
│   └── worker.py      # ARQ worker entry
├── prisma/
│   └── schema.prisma  # Database schema
├── requirements/      # prod.txt, dev.txt
├── seed/              # Seed scripts (e.g. seed_users_auth_data)
├── tests/
├── docs/              # Guides + PRODUCTION_READINESS.md
├── infra/             # Docker, start.sh
├── .env.example       # Env template (copy to .env)
├── Makefile           # install, generate, run, test, etc.
└── worker.sh          # Start ARQ worker
```

Each module uses **api/** (routes), **schemas/** (Pydantic), and **services/** (business logic).

---

## 📡 API overview

Base path: **`/api/v1`**

| Prefix            | Description                    |
|-------------------|--------------------------------|
| `/api/v1/auth`    | Login, register, refresh, logout, password reset |
| `/api/v1/users`   | User list, get, update, stats  |
| `/api/v1/restaurants` | Restaurants CRUD, gallery, menu |
| `/api/v1/cafes`   | Cafes CRUD, gallery, menu      |
| `/api/v1/bars`    | Bars CRUD, gallery, menu      |
| `/api/v1/attractions` | Attractions CRUD, gallery   |
| `/api/v1/souvenirs`   | Souvenirs CRUD, gallery, products |

**System**

- `GET /` — API info and loaded services
- `GET /health` — Health status
- `GET /api/v1/health` — Health + endpoint list
- `GET /docs` — Swagger UI

---

## 🚀 Production

- Set **`ENVIRONMENT=production`** and use explicit **`CORS_ORIGINS`** (no `*`).
- Use a strong **`JWT_SECRET`** and secure **DATABASE_URL**, **REDIS_URL**, and storage credentials.
- Run the API (e.g. Uvicorn with workers) and the ARQ worker as separate processes.

See **[docs/PRODUCTION_READINESS.md](docs/PRODUCTION_READINESS.md)** for a full checklist.

**Docker**: Use `infra/docker/Dockerfile`; see `infra/docker/docker-compose.prod.yaml` for a multi-service setup.

**Start script**: `infra/scripts/start.sh` (set `APP_DIR` and optionally `VENV_PATH` for your deployment).

---

## 🔧 Development

```bash
make lint      # Ruff
make format    # Black + Ruff
make typecheck # Mypy
make clean     # Remove caches
```

Database schema is in **`prisma/schema.prisma`**. After editing:

```bash
make generate
make migrate
```

---

## 🚨 Troubleshooting

| Issue | What to try |
|-------|-------------|
| **DB connection** | Check `DATABASE_URL` in `.env`; ensure PostgreSQL is running; `make migrate`. |
| **Prisma errors** | Run `make generate` from project root. |
| **Worker fails** | Ensure Redis is running and `REDIS_URL` in `.env` is correct; `redis-cli ping`. |
| **Port 8000 in use** | Use another port: `uvicorn app.main:app --port 8001` or stop the process using the port. |
| **Tests fail** | Run without Qdrant: `pytest tests/ --ignore=tests/test_restaurants_qdrant.py`. |
| **Import errors** | `make clean`, `make generate`, re-activate venv. |

---

## 📚 Docs & contact

- **[Production readiness](docs/PRODUCTION_READINESS.md)** — Env vars and deployment checklist
- **[Storage migration](docs/STORAGE_MIGRATION.md)** — Storage adapter usage
- **[Users API](docs/USERS_API.md)** — User endpoints
- **Swagger** — http://localhost:8000/docs

**Contact**: Bounyalith Chanrasanichone — bounyalith.c@gmail.com  

**License**: MIT
