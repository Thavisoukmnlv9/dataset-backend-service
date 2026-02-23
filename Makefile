.PHONY: help install dev lint format typecheck test test-cov run run-worker migrate seed clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Setup ────────────────────────────────────────────────────────────────────

install: ## Install production deps
	pip install -r requirements/prod.txt

dev: ## Install dev deps (includes prod)
	pip install -r requirements/dev.txt
	pip install ruff black pytest pytest-asyncio mypy httpx

# ── Quality ──────────────────────────────────────────────────────────────────

lint: ## Run ruff linter
	ruff check app/ tests/

format: ## Auto-format with black + ruff
	black app/ tests/
	ruff check --fix app/ tests/

typecheck: ## Run mypy type checker
	mypy app/ --ignore-missing-imports --no-error-summary || true

# ── Testing ──────────────────────────────────────────────────────────────────

test: ## Run all tests
	pytest tests/ -v --tb=short

test-cov: ## Run tests with coverage
	pytest tests/ -v --tb=short --cov=app --cov-report=term-missing

# ── Run ──────────────────────────────────────────────────────────────────────

run: ## Start the API server (dev)
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-worker: ## Start the ARQ background worker
	python -m app.worker

# ── Database ─────────────────────────────────────────────────────────────────

migrate: ## Run Prisma migrations
	prisma db push

generate: ## Generate Prisma client
	prisma generate

seed: ## Seed the database
	python -m seed.seed_users_auth_data

# ── Cleanup ──────────────────────────────────────────────────────────────────

clean: ## Remove caches and build artefacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf .ruff_cache htmlcov .coverage
