#!/bin/bash

# Tourism Middleware ARQ Worker Script
set -e

WORKER_MODULE="app.worker"
REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"

echo "🔄 Starting dataset ARQ Worker..."

# Check project directory
if [ ! -f "app/worker.py" ]; then
    echo "❌ Error: app/worker.py not found. Please run from project root."
    exit 1
fi

# Activate virtual environment
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "📦 Activating virtual environment..."
    source .venv/bin/activate
else
    echo "⚠️  No virtual environment found. Using system Python."
fi

# Check .env file
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Please run 'make setup' first."
    exit 1
fi

# Check Redis connection
echo "🔍 Checking Redis connection..."
if ! python3 -c "
import redis
try:
    r = redis.from_url('$REDIS_URL')
    r.ping()
    print('✅ Redis connected')
except Exception as e:
    print(f'❌ Redis connection failed: {e}')
    exit(1)
" 2>/dev/null; then
    echo "❌ Redis connection failed. Please ensure Redis is running."
    echo "💡 Start Redis with: redis-server or make docker-dev"
    exit 1
fi

# Start worker
echo "🚀 Starting ARQ worker..."
echo "📍 Redis: $REDIS_URL"
echo "📧 Processing background tasks"
echo "Press Ctrl+C to stop"
echo "================================="

exec python3 -m $WORKER_MODULE
