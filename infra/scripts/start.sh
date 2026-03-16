#!/bin/bash

# Tourism Middleware Production Startup Script

set -e  # Exit on any error

# Configuration (override APP_DIR for your deployment path)
APP_DIR="${APP_DIR:-/var/www/tourism-middleware}"
VENV_PATH="${VENV_PATH:-$APP_DIR/.venv}"
APP_MODULE="app.main:app"
HOST="0.0.0.0"
PORT="8000"
WORKERS="4"

echo "Starting Tourism Middleware API..."

# Check if we're in the right directory
if [ ! -d "$APP_DIR" ]; then
    echo "Error: Application directory not found: $APP_DIR"
    exit 1
fi

cd "$APP_DIR"

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo "Error: Virtual environment not found: $VENV_PATH"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_PATH/bin/activate"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Using default configuration."
fi

# Install/update dependencies
echo "Installing production dependencies..."
pip install -r requirements/prod.txt

# Generate Prisma client
echo "Generating Prisma client..."
prisma generate

# Start the application
echo "Starting FastAPI application on $HOST:$PORT..."

# Check if this is development or production environment
if [ "${ENVIRONMENT:-production}" = "development" ]; then
    # Development mode: Use fastapi dev for hot reload
    echo "Running in DEVELOPMENT mode with hot reload..."
    exec fastapi dev app/main.py \
        --host "$HOST" \
        --port "$PORT"
else
    # Production mode: Use fastapi run with workers
    echo "Running in PRODUCTION mode with $WORKERS workers..."
    exec fastapi run "$APP_MODULE" \
        --host "$HOST" \
        --port "$PORT" \
        --workers "$WORKERS"
fi

# Alternative: Using uvicorn directly (fallback option)
# echo "Using uvicorn with $WORKERS workers..."
# exec uvicorn "$APP_MODULE" \
#     --host "$HOST" \
#     --port "$PORT" \
#     --workers "$WORKERS" \
#     --log-level info
