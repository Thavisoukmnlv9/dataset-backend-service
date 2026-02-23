#!/bin/bash

# Tourism Middleware - Complete Setup Script
# This script sets up the entire development environment

set -e

echo "🏗️  Setting up Tourism Middleware development environment..."

# Check if Python 3.13+ is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.13 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.13"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Python $REQUIRED_VERSION or higher is required. Current version: $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python $PYTHON_VERSION detected"

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install development dependencies
echo "📚 Installing development dependencies..."
pip install -r requirements/dev.txt

# Create .env file from example
if [ ! -f .env ]; then
    echo "📝 Creating .env file from example..."
    cp env.example .env
    echo "⚠️  Please update .env file with your actual configuration values"
else
    echo "✅ .env file already exists"
fi

# Fix environment configuration if requested
if [ "$1" = "--fix-env" ] || [ "$2" = "--fix-env" ] || [ "$3" = "--fix-env" ]; then
    echo "🔧 Fixing environment configuration..."
    # Update DATABASE_URL with proper credentials
    echo "📝 Updating DATABASE_URL with proper credentials..."
    sed -i '' 's/postgresql:\/\/username:password@localhost:5432\/tourism_db/postgresql:\/\/tourism_user:tourism_password@localhost:5432\/tourism_db/' .env
    # Update JWT_SECRET with a random value
    echo "🔐 Generating a random JWT secret..."
    RANDOM_JWT=$(openssl rand -hex 32)
    sed -i '' "s/your-super-secret-jwt-key-here/$RANDOM_JWT/" .env
    echo "✅ Environment configuration updated!"
    echo "📋 Updated configuration:"
    echo "   - DATABASE_URL: postgresql://tourism_user:tourism_password@localhost:5432/tourism_db"
    echo "   - JWT_SECRET: Generated random secret"
fi

# Generate Prisma client
echo "🔧 Generating Prisma client..."
prisma generate

# Setup database (optional)
echo "🗄️  Setting up database..."
if [ "$1" = "--with-db" ]; then
    echo "📊 Pushing database schema..."
    prisma db push
    
    if [ "$2" = "--seed" ]; then
        echo "🌱 Seeding database with sample data..."
        if [ -f "seed_mvp_data.py" ]; then
            python seed_mvp_data.py
        else
            echo "⚠️  seed_mvp_data.py not found, skipping seeding"
        fi
    fi
else
    echo "💡 To setup database, run: ./setup_venv.sh --with-db"
    echo "💡 To also seed database, run: ./setup_venv.sh --with-db --seed"
fi

echo ""
echo "🎉 Setup complete! To get started:"
echo ""
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Update your .env file with actual configuration values"
echo ""
echo "3. Start the development server:"
echo "   ./dev.sh                    # Development mode"
echo "   ./dev.sh production         # Production mode"
echo ""
echo "4. Or use Docker Compose:"
echo "   docker-compose -f docker-compose.dev.yaml up -d"
echo ""
echo "5. Access the application:"
echo "   - API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - Prisma Studio: http://localhost:5555"
echo ""
echo "💡 Available setup options:"
echo "   ./setup_venv.sh                    # Basic setup"
echo "   ./setup_venv.sh --with-db          # With database"
echo "   ./setup_venv.sh --with-db --seed   # With database + seed data"
echo "   ./setup_venv.sh --fix-env          # Fix environment config"
echo ""
echo "Happy coding! 🚀"
