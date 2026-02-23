#!/bin/bash

# dataset - Seed Data Script (User & Auth only)

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo -e "${BLUE}🚀 dataset - Seed Data (User & Auth)${NC}"
echo ""

print_status() { echo -e "${GREEN}✅ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_header() { echo -e "${BLUE}📋 $1${NC}"; }

check_venv() {
    if [ ! -d "$PROJECT_ROOT/venv" ]; then
        print_error "Virtual environment not found at $PROJECT_ROOT/venv"
        exit 1
    fi
}

activate_venv() {
    print_info "Activating virtual environment..."
    source "$PROJECT_ROOT/venv/bin/activate"
    print_status "Virtual environment activated"
}

check_database() {
    print_info "Checking database connection..."
    cd "$PROJECT_ROOT"
    python -c "
import asyncio
import sys
from app.prisma import connect_db, disconnect_db

async def test_connection():
    try:
        await connect_db()
        print('Database connection successful')
        await disconnect_db()
        return True
    except Exception as e:
        print(f'Database connection failed: {e}')
        return False

if not asyncio.run(test_connection()):
    sys.exit(1)
"
    print_status "Database connection verified"
}

seed_users_auth() {
    print_header "Seeding Users & Auth Data"
    print_info "Creating sample users with authentication..."
    cd "$PROJECT_ROOT"
    python -m seed.seed_users_auth_data
    if [ $? -eq 0 ]; then
        print_status "Users auth seed completed successfully"
    else
        print_error "Users auth seed failed"
        return 1
    fi
}

seed_clear_all() {
    print_header "Clearing All Database Data"
    print_warning "This will delete ALL data from the database!"
    cd "$PROJECT_ROOT"
    python -c "
import asyncio
from app.prisma import prisma, connect_db, disconnect_db

async def clear_all_data():
    await connect_db()
    print('🗑️  Clearing sessions...')
    await prisma.session.delete_many()
    print('🗑️  Clearing refresh tokens...')
    await prisma.refreshtoken.delete_many()
    print('🗑️  Clearing device tokens...')
    await prisma.devicetoken.delete_many()
    print('🗑️  Clearing API keys...')
    await prisma.apikey.delete_many()
    print('🗑️  Clearing users...')
    await prisma.user.delete_many()
    print('🎉 All database data cleared successfully!')
    await disconnect_db()

asyncio.run(clear_all_data())
"
    if [ $? -eq 0 ]; then
        print_status "Database cleared successfully"
        print_info "Run './seed/seed.sh users-auth' to recreate users."
    else
        print_error "Failed to clear database"
        return 1
    fi
}

show_help() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  users-auth   Seed users and auth data (default)"
    echo "  clear-all    Clear all data from database (DANGEROUS!)"
    echo "  help         Show this help"
    echo ""
    echo "Examples:"
    echo "  $0              # Seed users/auth"
    echo "  $0 users-auth   # Seed users/auth"
    echo "  $0 clear-all   # Clear all data"
}

main() {
    cd "$PROJECT_ROOT"
    case "${1:-users-auth}" in
        "users-auth")
            check_venv
            activate_venv
            check_database
            seed_users_auth
            ;;
        "clear-all")
            check_venv
            activate_venv
            check_database
            seed_clear_all
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
