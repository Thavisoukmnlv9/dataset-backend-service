# Tourism Middleware API

A modern FastAPI-based authentication service for the Tourism Ticketing project.

## 🚀 Features

- **User Authentication**: Registration and login with JWT tokens
- **Password Security**: BCrypt hashing with configurable rounds
- **Input Validation**: Comprehensive Pydantic models with validation
- **CORS Support**: Configurable cross-origin resource sharing
- **Request Logging**: Detailed request/response logging
- **Health Checks**: Monitoring endpoints
- **API Documentation**: Auto-generated Swagger/OpenAPI docs

## 🏗️ Architecture

The project follows a **modular architecture** with clear separation of concerns:

```
tourism-backend-service/
├── app/
│   ├── core/                  # Core application configuration
│   │   ├── config.py          # Settings and configuration
│   │   ├── security.py        # Authentication & authorization
│   │   └── ...
│   ├── modules/               # Business domain modules
│   │   ├── users/             # User management module
│   │   │   ├── api/           # FastAPI routes
│   │   │   ├── schemas/       # Pydantic models
│   │   │   └── services/      # Business logic
│   │   ├── auth/              # Authentication module
│   │   ├── attractions/       # Attractions module
│   │   ├── vendors/           # Vendor management
│   │   └── ...                # Other business modules
│   ├── shared/                # Shared utilities and services
│   │   ├── services/          # Common services (email, file upload, etc.)
│   │   ├── schemas/           # Base schemas and common models
│   │   └── utils/             # Utility functions
│   ├── prisma/                # Prisma database client
│   ├── main.py                # FastAPI application entrypoint
│   └── worker.py              # ARQ background worker
├── docs/                      # API documentation and guides
│   ├── RESPONSE_FORMAT_GUIDE.md    # API response standards
│   ├── MODULE_STRUCTURE_GUIDE.md   # Module business guide
│   └── ...                    # Other API documentation
├── infra/                     # Infrastructure and deployment
│   ├── scripts/               # Setup and utility scripts
│   │   └── Makefile           # Development commands
│   ├── docker/                # Docker configurations
│   └── env/                   # Environment templates
├── seed/                      # Database seeding scripts
├── prisma/                    # Database schema and migrations
├── requirements/              # Python dependencies
├── dev.sh                     # Development server script
├── worker.sh                  # Background worker script
└── README.md                  # This file
```

### 📚 Documentation

- **[Response Format Guide](docs/RESPONSE_FORMAT_GUIDE.md)** - Standardized API response formats
- **[Module Structure Guide](docs/MODULE_STRUCTURE_GUIDE.md)** - Module business patterns
- **[API Documentation](docs/)** - Individual module API documentation

### 🏛️ Module Structure Example

Each business module follows a consistent structure. Here's the `users` module as an example:

```
app/modules/users/
├── api/
│   ├── __init__.py
│   └── routes.py              # FastAPI route definitions
├── schemas/
│   ├── __init__.py
│   └── user.py                # Pydantic models for validation
└── services/
    ├── __init__.py
    ├── create.py              # User creation business logic
    ├── get_one.py             # Single user retrieval
    ├── get_list.py            # User listing and search
    ├── update.py              # User update operations
    ├── delete.py              # User deletion
    ├── lookup.py              # User lookup utilities
    └── stats.py               # User statistics
```

**Layer Responsibilities:**
- **API Layer** (`api/`) - HTTP endpoints and request handling
- **Schemas Layer** (`schemas/`) - Data validation and serialization
- **Services Layer** (`services/`) - Business logic and orchestration

This pattern ensures clear separation of concerns, testability, and maintainability across all modules.

## 📋 Prerequisites

- Python 3.13+
- PostgreSQL database
- Prisma CLI

## 🛠️ Installation

### Quick Setup (Recommended)

```bash
# Clone the repository
git clone https://github.com/TourismCloud/tourism-backend-service.git
cd tourism-backend-service

# Navigate to scripts directory
cd infra/scripts

# Run complete setup (creates venv, installs deps, sets up database)
make setup
```

### Manual Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/TourismCloud/tourism-backend-service.git
   cd tourism-backend-service
   ```

2. **Create virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements/dev.txt
   ```

4. **Set up environment variables**

   ```bash
   cp infra/env/env.example .env
   # Edit .env with your configuration
   ```

5. **Set up database**

   ```bash
   # Generate Prisma client
   prisma generate

   # Run database migrations
   prisma migrate dev --name init

   # Push schema to database
   prisma db push
   ```

6. **Seed the database (optional)**

   ```bash
   cd seed
   ./seed.sh users-auth  # Start with basic auth data
   ```

## ⚙️ Configuration

The project uses environment variables for configuration. Copy the example file and customize it:

```bash
# Copy environment template
cp infra/env/env.example .env

# Edit with your configuration
nano .env  # or your preferred editor
```

**Key Configuration Variables:**

```env
# Database Configuration
DATABASE_URL="postgresql://pern:welcome@localhost:5432/kanom"

# JWT Configuration - Tourism Optimized
# Access Token: 60 minutes - Good balance of security and user experience
# Refresh Token: 30 days - Better for travel planning and return users
JWT_SECRET="your-super-secret-jwt-key-here"
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30

# CORS Configuration
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
CORS_ALLOW_HEADERS=["*"]

# API Configuration
API_TITLE="Tourism Middleware API"
API_DESCRIPTION="API documentation for user authentication in the Tourism Middleware project."
API_VERSION="1.0.0"

# Security Configuration
BCRYPT_ROUNDS=12

# Logging Configuration
LOG_LEVEL="INFO" 

# Frontend URL for building reset links
FRONTEND_URL="http://localhost:5173"

# MinIO Storage Configuration
MINIO_ENDPOINT="localhost:9000"
MINIO_ACCESS_KEY="minioadmin"
MINIO_SECRET_KEY="minioadmin123"
MINIO_SECURE=false
MINIO_PUBLIC_URL="http://localhost:9000"
MINIO_ENABLED=true
# File Upload Configuration
MAX_FILE_SIZE=52428800
ALLOWED_FILE_TYPES=["image/jpeg", "image/png", "image/gif", "image/svg+xml", "application/pdf"]

# Redis Configuration
REDIS_HOST="localhost"
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=""
REDIS_URL="redis://localhost:6379/0"

# RedisInsight Configuration (for development)
REDISINSIGHT_URL="http://localhost:8001"

MAIL_HOST=smtp-relay.brevo.com
MAIL_PORT=587
MAIL_USERNAME=<your-sendinblue-smtp-username>
MAIL_PASSWORD=<your-sendinblue-smtp-api-key>
MAIL_FROM_EMAIL=<your-from-email>
MAIL_FROM_NAME=kanom
MAIL_USE_TLS=true
MAIL_USE_SSL=false

```

**Environment Files:**
- `infra/env/env.example` - Template with all available variables
- `.env` - Your local configuration (created during setup)

## 🚀 Running the Application

### Quick Start with Makefile (Recommended) 🚀

The easiest way to get started is using the Makefile commands:

```bash
# Navigate to the scripts directory
cd infra/scripts

# First time setup (creates venv, installs deps, sets up database)
make setup

# Start development server
make dev

# Start background worker (in another terminal)
make worker

# Show all available commands
make help
```

### Development Scripts

**Option 1: Using the development script (Recommended)**

```bash
# Start FastAPI development server
./dev.sh

# Start ARQ background worker (in another terminal)
./worker.sh
```

**Option 2: Using Makefile commands**

```bash
cd infra/scripts

# Development server
make dev

# Background worker
make worker

# Database operations
make migrate          # Run database migrations
make db-sync          # Generate client, migrate, and push schema
make db-init          # Initialize database with dev migration
```

**Option 3: Using FastAPI CLI**

```bash
# Development
fastapi dev main.py --host 127.0.0.1 --port 8000

# Production
fastapi run main.py --host 0.0.0.0 --port 8000 --workers 4
```

**Option 4: Using Uvicorn directly**

```bash
# Development
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Available Makefile Commands

```bash
cd infra/scripts && make help
```

**Setup Commands:**
- `make setup` - First time setup (venv, deps, database)
- `make migrate` - Run database migrations
- `make db-init` - Generate client, migrate dev, and push schema
- `make db-sync` - Generate client, migrate, and push schema

**Development Commands:**
- `make dev` - Start development server
- `make worker` - Start ARQ worker for background tasks

**Production Commands:**
- `make prod` - Start production server

**Docker Commands:**
- `make docker-dev` - Start development environment with Docker
- `make docker-prod` - Start production environment with Docker
- `make docker-down` - Stop all Docker services
- `make docker-build` - Build Docker image for production
- `make docker-build-dev` - Build Docker image for development

**Utility Commands:**
- `make clean` - Clean up temporary files
- `make logs` - Show application logs
- `make fix-env` - Fix environment configuration

### Database Seeding

The project includes comprehensive seeding scripts for development and testing:

```bash
# Navigate to seed directory
cd seed

# Show all available seed options
./seed.sh help

# Run all seed data
./seed.sh

# Run specific seed data
./seed.sh users-auth        # Users and authentication data
./seed.sh business     # Business data
./seed.sh rbac-roles        # RBAC roles and permissions
./seed.sh attractions       # Tourist attractions data
./seed.sh vendors           # Vendor profiles
./seed.sh tourists          # Tourist profiles
./seed.sh passports         # Passport data
./seed.sh kyc-records       # KYC verification records

# Run all authentication-related data
./seed.sh auth-all

# Clear all data (DANGEROUS!)
./seed.sh clear-all
```

**Available Seed Commands:**
- `attractions` - Tourist attractions and locations
- `vendors` - Vendor profiles and business data
- `business` - Business and company data
- `users-auth` - User accounts and authentication
- `rbac-roles` - Role-based access control roles
- `user-roles` - User role assignments
- `accounts` - User account profiles
- `tourists` - Tourist profile data
- `passports` - Passport and travel documents
- `kyc-records` - Know Your Customer verification
- `session-test` - Session testing data
- `auth-all` - All authentication-related data
- `seed-all` - Users-auth seed data only
- `clear-all` - Clear all database data (DANGEROUS!)

### Production

**Option 1: Using FastAPI run**

```bash
fastapi run main.py --host 0.0.0.0 --port 8000 --workers 4
```

**Option 2: Using Uvicorn (Recommended)**

```bash
chmod +x start.sh
./start.sh
```

## 🔄 FastAPI vs Uvicorn: Which to Use?

### **FastAPI CLI (`fastapi run/dev`)**

- ✅ **Simpler syntax** - fewer options to remember
- ✅ **Auto-detection** - automatically finds your app
- ✅ **Smart defaults** - optimized for FastAPI
- ✅ **Built-in features** - handles common FastAPI scenarios
- ✅ **Now working** - fixed import issues
- ❌ **Limited control** - fewer configuration options

### **Uvicorn (Direct ASGI Server)**

- ✅ **More control** - extensive configuration options
- ✅ **Universal** - works with any ASGI framework
- ✅ **Production-ready** - more server-specific options
- ✅ **Performance tuning** - detailed performance configurations
- ✅ **Reliable imports** - handles complex module structures better
- ❌ **More complex** - more options to configure

### **Recommendation:**

- **Development**: Use `fastapi dev` (now working with simplified imports)
- **Production**: Use `uvicorn` (more control, better performance)

## ✅ FastAPI CLI Now Working!

The FastAPI CLI import issues have been resolved by:

1. **Simplifying imports** in `app/main.py`
2. **Deferring complex imports** to the lifespan function
3. **Creating a simple entry point** in `main.py`

**Working commands:**

```bash
# Development
fastapi dev main.py --host 127.0.0.1 --port 8000

# Production
fastapi run main.py --host 0.0.0.0 --port 8000 --workers 4
```

## 📚 API Documentation

### Interactive Documentation

- **Swagger UI**: `http://localhost:8000/docs` - Interactive API documentation
- **ReDoc**: `http://localhost:8000/redoc` - Alternative documentation format

### API Response Format

All API responses follow a standardized format for consistency:

```json
{
  "success": true,
  "data": <response_data>,
  "message": "Operation successful",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

For detailed response format specifications, see the [Response Format Guide](docs/RESPONSE_FORMAT_GUIDE.md).

### Available Modules

The API is organized into business domain modules:

**Authentication & User Management:**
- **`/api/v1/auth/`** - Authentication endpoints (login, register, password reset)
- **`/api/v1/users/`** - User profile management and operations

**Tourism Business:**
- **`/api/v1/attractions/`** - Tourist attractions and locations
- **`/api/v1/vendors/`** - Vendor profiles and business management
- **`/api/v1/tourists/`** - Tourist profiles and preferences
- **`/api/v1/business/`** - Business and company management

**Travel Documents & Verification:**
- **`/api/v1/passports/`** - Passport management and verification
- **`/api/v1/kyc/`** - Know Your Customer verification processes

**Access Control:**
- **`/api/v1/rbac_roles/`** - Role-based access control and permissions

**System:**
- `GET /` - API information
- `GET /api/v1/health` - Health check
- `GET /docs` - Swagger documentation

### Module Structure

Each module follows the consistent pattern:
```
app/modules/{module_name}/
├── api/           # FastAPI routes and endpoints
├── schemas/       # Pydantic models and validation
└── services/      # Business logic and operations
```

**Available Modules:**
- **`auth/`** - User authentication and authorization
- **`users/`** - User profile and account management
- **`business/`** - Business and company profiles
- **`attractions/`** - Tourist attractions and destinations
- **`vendors/`** - Vendor business profiles and services
- **`tourists/`** - Tourist profiles and travel preferences
- **`passport/`** - Passport and travel document management
- **`kyc/`** - Identity verification and compliance
- **`rbac_roles/`** - Role-based access control system

For complete API documentation, see the individual module guides in the [docs/](docs/) directory.

## 🔒 Security Features

- **JWT Tokens**: Secure authentication with configurable expiration
- **Password Hashing**: BCrypt with configurable rounds
- **Input Validation**: Comprehensive validation using Pydantic
- **CORS Protection**: Configurable cross-origin policies
- **Request Logging**: Security event tracking

## 📊 Database Schema

```prisma
model User {
  id        String   @id @default(uuid())
  email     String   @unique
  password  String
  createdAt DateTime @default(now())
  isActive  Boolean  @default(true)
}
```

## 🧪 Testing

```bash
# Run tests (when implemented)
pytest

# Run with coverage
pytest --cov=app
```

## 📦 Deployment

### Docker (Recommended)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN prisma generate

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### DigitalOcean (Current)

The project includes GitHub Actions for automatic deployment to DigitalOcean.

## 🔧 Development

### Code Generation

```bash
# Generate Prisma client after schema changes
prisma generate

# Update database schema
prisma db push
```

### Code Quality

```bash
# Format code
black app/

# Lint code
flake8 app/

# Type checking
mypy app/
```

## 📈 Monitoring

- **Health Check**: `/api/v1/health`
- **Request Logging**: All requests are logged with timing
- **Error Tracking**: Comprehensive error handling and logging

## 🚨 Troubleshooting

### Common Issues

**1. Setup Issues**

```bash
# If make setup fails, try manual setup
cd infra/scripts
make clean
make setup

# Or fix environment configuration
make fix-env
```

**2. Environment Variables Missing**

```bash
# Copy and configure environment file
cp infra/env/env.example .env
# Edit .env with your actual values
```

**3. Database Connection Issues**

```bash
# Check PostgreSQL is running
brew services list | grep postgresql

# Reset database
cd infra/scripts
make db-sync

# Or start fresh
make db-init
```

**4. Port Already in Use**

```bash
# Kill existing process
lsof -ti:8000 | xargs kill -9

# Or use different port
./dev.sh  # Will automatically handle port conflicts
```

**5. Redis Connection Issues (for background worker)**

```bash
# Start Redis server
redis-server

# Or use Docker
make docker-dev
```

**6. Module Import Issues**

```bash
# Regenerate Prisma client
prisma generate

# Clear Python cache
make clean

# Reinstall dependencies
pip install -r requirements/dev.txt
```

### Quick Fixes

```bash
# Navigate to scripts directory
cd infra/scripts

# Clean and reset everything
make clean
make setup

# Or just fix specific issues
make fix-env          # Fix environment configuration
make db-sync          # Sync database
make logs             # Check application logs
```

### Development Script Issues

**If `./dev.sh` fails:**
```bash
# Check if virtual environment is activated
source venv/bin/activate

# Check if .env file exists
ls -la .env

# Run with verbose output
bash -x ./dev.sh
```

**If `./worker.sh` fails:**
```bash
# Check Redis connection
redis-cli ping

# Check if .env file exists
ls -la .env

# Run with verbose output
bash -x ./worker.sh
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 👥 Contact

- **Developer**: Bounyalith Chanrasanichone
- **Email**: bounyalith.c@gmail.com


