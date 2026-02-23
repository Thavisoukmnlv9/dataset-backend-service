# Tourism Middleware - Makefile
# Common commands for development and deployment

.PHONY: all make help setup dev prod worker clean docker-dev docker-prod docker-down docker-build docker-build-dev migrate db-init db-sync logs fix-env

# Default target
all: help

# Default target (same as help)
make: help

help:
	@echo "Tourism Middleware - Available Commands:"
	@echo ""
	@echo "Quick Start (copy & paste):"
	@echo "  make setup     - First time setup"
	@echo "  make dev       - Start development server"
	@echo "  make docker-dev - Start with Docker"
	@echo ""
	@echo "Setup:"
	@echo " make setup             - Set up virtual environment and install dependencies"
	@echo " make migrate           - Run database migrations"
	@echo " make db-init           - Generate client, migrate dev, and push schema"
	@echo " make db-sync           - Generate client, migrate, and push schema"
	@echo ""
	@echo "Development:"
	@echo " make dev               - Start development server"
	@echo " make worker            - Start ARQ worker for background tasks"
	@echo ""
	@echo "Production:"
	@echo " make prod              - Start production server"
	@echo ""
	@echo "Docker:"
	@echo " make docker-dev        - Start development environment with Docker"
	@echo " make docker-prod       - Start production environment with Docker"
	@echo " make docker-down       - Stop all Docker services"
	@echo " make docker-build      - Build Docker image for production"
	@echo " make docker-build-dev  - Build Docker image for development"
	@echo ""
	@echo "Utilities:"
	@echo " make clean             - Clean up temporary files"
	@echo " make logs              - Show application logs"
	@echo " make fix-env           - Fix environment configuration"

# Setup virtual environment
setup:
	@echo "Setting up virtual environment..."
	@cd ../.. && \
	if [ ! -d "venv" ]; then \
		echo "🔧 Creating virtual environment..."; \
		python3 -m venv venv; \
	fi && \
	echo "📦 Activating virtual environment and installing dependencies..."; \
	source venv/bin/activate && \
	pip install --upgrade pip && \
	pip install -r requirements/dev.txt && \
	echo "⚙️ Creating .env file..."; \
	if [ ! -f ".env" ]; then \
		cp infra/env/env.example .env; \
		echo "🔐 Generating secure JWT_SECRET..."; \
		JWT_SECRET=$$(python3 -c "import secrets; print(secrets.token_urlsafe(255))"); \
		sed -i.bak "s/JWT_SECRET=\"dev-secret-key-change-in-production\"/JWT_SECRET=\"$$JWT_SECRET\"/" .env; \
		rm -f .env.bak; \
		echo "✅ .env file created with secure JWT_SECRET"; \
	else \
		echo "ℹ️ .env file already exists"; \
	fi && \
	echo "🗄️ Setting up database..."; \
	set -a && \
	source .env && \
	set +a && \
	prisma generate && \
	prisma migrate dev --name init && \
	prisma db push && \
	echo "✅ Setup completed successfully!"

# Database operations
migrate:
	@echo "Running database migrations..."
	@cd ../.. && \
	if [ ! -d "venv" ]; then \
		echo "❌ Virtual environment not found. Please run setup first:"; \
		echo "   make setup"; \
		exit 1; \
	fi && \
	if [ ! -f ".env" ]; then \
		echo "❌ .env file not found. Please run setup first:"; \
		echo "   make setup"; \
		exit 1; \
	fi && \
	source venv/bin/activate && \
	set -a && \
	source .env && \
	set +a && \
	prisma generate && \
	prisma db push

db-sync:
	@echo "Syncing database: Generate client, migrate, and push schema..."
	@cd ../.. && \
	if [ ! -d "venv" ]; then \
		echo "❌ Virtual environment not found. Please run setup first:"; \
		echo "   make setup"; \
		exit 1; \
	fi && \
	if [ ! -f ".env" ]; then \
		echo "❌ .env file not found. Please run setup first:"; \
		echo "   make setup"; \
		exit 1; \
	fi && \
	source venv/bin/activate && \
	set -a && \
	source .env && \
	set +a && \
	echo "🔧 Generating Prisma client..." && \
	prisma generate && \
	echo "📊 Pushing database schema..." && \
	prisma db push && \
	echo "✅ Database sync completed successfully!"

db-init:
	@echo "Initializing database with dev migration..."
	@cd ../.. && \
	if [ ! -d "venv" ]; then \
		echo "❌ Virtual environment not found. Please run setup first:"; \
		echo "   make setup"; \
		exit 1; \
	fi && \
	if [ ! -f ".env" ]; then \
		echo "❌ .env file not found. Please run setup first:"; \
		echo "   make setup"; \
		exit 1; \
	fi && \
	source venv/bin/activate && \
	set -a && \
	source .env && \
	set +a && \
	echo "🔧 Generating Prisma client..." && \
	prisma generate && \
	echo "📊 Running migration in dev mode..." && \
	prisma migrate dev --name init && \
	echo "🚀 Pushing database schema..." && \
	prisma db push && \
	echo "✅ Database migration completed successfully!"

# Development
dev:
	@echo "Starting development server..."
	@cd ../.. && ./dev.sh

worker:
	@echo "Starting ARQ worker..."
	@cd ../.. && ./worker.sh

prod:
	@echo "Starting production server..."
	@cd ../.. && ./dev.sh production

# Docker operations
docker-dev:
	@echo "Starting development environment with Docker..."
	@cd ../.. && docker-compose -f infra/docker/docker-compose.dev.yaml up -d

docker-prod:
	@echo "Starting production environment with Docker..."
	@cd ../.. && docker-compose -f infra/docker/docker-compose.prod.yaml up -d

docker-down:
	@echo "Stopping Docker services..."
	@cd ../.. && docker-compose -f infra/docker/docker-compose.dev.yaml down
	@cd ../.. && docker-compose -f infra/docker/docker-compose.prod.yaml down

docker-build:
	@echo "Building Docker image for production..."
	@cd ../.. && docker build -f infra/docker/Dockerfile -t tourism-api:latest .

docker-build-dev:
	@echo "Building Docker image for development..."
	@cd ../.. && docker build -f infra/docker/Dockerfile.dev -t tourism-api:dev .

# Utilities
clean:
	@echo "Cleaning up..."
	@cd ../.. && find . -type f -name "*.pyc" -delete
	@cd ../.. && find . -type d -name "__pycache__" -delete
	@cd ../.. && find . -type d -name "*.egg-info" -exec rm -rf {} +
	@cd ../.. && rm -rf .pytest_cache
	@cd ../.. && rm -rf .mypy_cache

logs:
	@echo "Showing application logs..."
	@cd ../.. && docker-compose -f infra/docker/docker-compose.dev.yaml logs -f

fix-env:
	@echo "Fixing environment configuration..."
	@cd ../.. && ./infra/scripts/setup_venv.sh --fix-env