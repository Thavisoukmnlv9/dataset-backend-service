from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ========================================
    # COMMON SETTINGS
    # ========================================

    # Environment
    environment: str = Field(
        default="development", description="Environment (development/production)", alias="ENVIRONMENT")

    # Domain
    domain: str = Field(default="http://kanom.duckdns.org",
                        description="Domain", alias="DOMAIN")

    # JWT Configuration
    jwt_secret: str = Field(
        default="dev-secret-key-change-in-production",
        description="JWT secret key",
        alias="JWT_SECRET"
    )
    access_token_expire_minutes: int = Field(
        default=240, description="JWT token expiration time (4 hours for admin portal)", alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(
        default=30, description="JWT refresh token expiration time (30 days for tourism UX)", alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # API Settings
    api_title: str = Field(default="Tourism Middleware API",
                           description="API title", alias="API_TITLE")
    api_description: str = Field(default="API documentation for user authentication in the Tourism Middleware project.",
                                 description="API description", alias="API_DESCRIPTION")
    api_version: str = Field(
        default="1.0.0", description="API version", alias="API_VERSION")

    # Security
    bcrypt_rounds: int = Field(
        default=12, description="BCrypt rounds for password hashing", alias="BCRYPT_ROUNDS")

    # Logging
    log_level: str = Field(
        default="INFO", description="Logging level", alias="LOG_LEVEL")

    # File Upload Settings
    max_file_size: int = Field(
        default=52428800, description="Maximum file size in bytes (50MB)", alias="MAX_FILE_SIZE")
    max_video_file_size: int = Field(
        default=1073741824, description="Maximum video file size in bytes (1GB)", alias="MAX_VIDEO_FILE_SIZE")
    allowed_file_types: list[str] = Field(
        default=["image/jpeg", "image/png", "image/gif", "image/svg+xml", "application/pdf",
                 "video/mp4", "video/avi", "video/mov", "video/wmv", "video/flv", "video/webm"],
        description="Allowed file types for upload",
        alias="ALLOWED_FILE_TYPES"
    )

    # ========================================
    # DATABASE
    # ========================================

    database_url: str = Field(
        default="postgresql://username:password@localhost:5432/tourism_db",
        description="PostgreSQL database URL",
        alias="DATABASE_URL"
    )
    # ========================================
    # GEMINI
    # ========================================
    gemini_api_key: str = Field(
        default="AIzaSyDUORhtRBnzEhbIgJAPcfNvx5XiZlht12c",
        description="Gemini API key",
        alias="GEMINI_API_KEY"
    )
    # ========================================
    # QDRANT
    # ========================================
    qdrant_url: str = Field(
        default="http://localhost:6333",
        description="Qdrant URL",
        alias="QDRANT_URL"
    )
    qdrant_api_key: str = Field(
        default="",
        description="Qdrant API key",
        alias="QDRANT_API_KEY"
    )
    # ========================================
    # CORS SETTINGS
    # ========================================

    cors_origins: list[str] = Field(
        default=["http://localhost:3000",  "http://localhost:3001",  "http://192.168.0.104:3000"],
        description="CORS origins",
        alias="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(
        default=True, description="CORS credentials", alias="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: list[str] = Field(
        default=["*"], description="CORS methods", alias="CORS_ALLOW_METHODS")
    cors_allow_headers: list[str] = Field(
        default=["*"], description="CORS headers", alias="CORS_ALLOW_HEADERS")

    # ========================================
    # EMAIL SETTINGS
    # ========================================

    smtp_host: str = Field(default="smtp-relay.brevo.com",
                           description="SMTP host", alias="MAIL_HOST")
    smtp_port: int = Field(
        default=587, description="SMTP port", alias="MAIL_PORT")
    smtp_username: Optional[str] = Field(
        default=None, description="SMTP username", alias="MAIL_USERNAME")
    smtp_password: Optional[str] = Field(
        default=None, description="SMTP password", alias="MAIL_PASSWORD")
    smtp_from_email: str = Field(
        default="noreply@kanom.com", description="From email", alias="MAIL_FROM_EMAIL")
    smtp_from_name: str = Field(
        default="kanom", description="From name", alias="MAIL_FROM_NAME")
    smtp_use_tls: bool = Field(
        default=True, description="Use TLS", alias="MAIL_USE_TLS")
    smtp_use_ssl: bool = Field(
        default=False, description="Use SSL", alias="MAIL_USE_SSL")
    frontend_url: str = Field(
        default="http://localhost:5173", description="Frontend URL", alias="FRONTEND_URL")
    vendor_portal_url: str = Field(
        default="http://localhost:8080", description="Vendor Portal URL", alias="VENDOR_PORTAL_URL")

    # ========================================
    # STORAGE (Port/Adapter: local | minio | s3 | wasabi)
    # ========================================

    storage_provider: str = Field(
        default="local",
        description="Storage provider: local, minio, s3, wasabi",
        alias="STORAGE_PROVIDER",
    )
    # Local filesystem (used when storage_provider=local)
    storage_local_base_dir: str = Field(
        default="uploads",
        description="Local base directory for uploads",
        alias="STORAGE_LOCAL_BASE_DIR",
    )
    storage_local_public_base_url: str = Field(
        default="/uploads",
        description="Public URL prefix for local files (e.g. /uploads)",
        alias="STORAGE_LOCAL_PUBLIC_BASE_URL",
    )
    # Remote object storage (minio, s3, wasabi)
    storage_bucket: str = Field(
        default="kanom-media",
        description="Bucket name for object storage",
        alias="STORAGE_BUCKET",
    )
    storage_region: Optional[str] = Field(
        default=None,
        description="Region for S3/Wasabi",
        alias="STORAGE_REGION",
    )
    storage_endpoint: Optional[str] = Field(
        default=None,
        description="Custom endpoint for MinIO/Wasabi (e.g. minio:9000 or s3.wasabisys.com)",
        alias="STORAGE_ENDPOINT",
    )
    storage_access_key: Optional[str] = Field(
        default=None,
        description="Access key for object storage",
        alias="STORAGE_ACCESS_KEY",
    )
    storage_secret_key: Optional[str] = Field(
        default=None,
        description="Secret key for object storage",
        alias="STORAGE_SECRET_KEY",
    )
    storage_use_ssl: bool = Field(
        default=False,
        description="Use SSL for object storage",
        alias="STORAGE_USE_SSL",
    )
    storage_presign_expires_seconds: int = Field(
        default=86400,
        description="Presigned URL expiry in seconds (default 24h)",
        alias="STORAGE_PRESIGN_EXPIRES_SECONDS",
    )
    storage_public_base_url: Optional[str] = Field(
        default=None,
        description="Public base URL for object storage (e.g. https://cdn.example.com)",
        alias="STORAGE_PUBLIC_BASE_URL",
    )

    # ========================================
    # MINIO SETTINGS (used when storage_provider=minio; kept for backward compatibility)
    # ========================================

    minio_endpoint: str = Field(
        default="localhost:9000", description="MinIO endpoint", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(
        default="", description="MinIO access key", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(
        default="", description="MinIO secret key", alias="MINIO_SECRET_KEY")
    minio_secure: bool = Field(
        default=False, description="MinIO secure", alias="MINIO_SECURE")
    minio_public_url: str = Field(
        default="http://localhost:9000", description="MinIO public URL", alias="MINIO_PUBLIC_URL")
    minio_enabled: bool = Field(
        default=True, description="MinIO enabled", alias="MINIO_ENABLED")

    # ========================================
    # REDIS SETTINGS
    # ========================================

    redis_host: str = Field(default="localhost",
                            description="Redis host", alias="REDIS_HOST")
    redis_port: int = Field(
        default=6379, description="Redis port", alias="REDIS_PORT")
    redis_db: int = Field(
        default=0, description="Redis database number", alias="REDIS_DB")
    redis_password: Optional[str] = Field(
        default="", description="Redis password", alias="REDIS_PASSWORD")
    redis_url: str = Field(default="redis://localhost:6379/0",
                           description="Redis URL", alias="REDIS_URL")

    # ========================================
    # INFRASTRUCTURE URLS
    # ========================================

    api_url: str = Field(default="http://localhost:8000",
                         description="API URL", alias="API_URL")
    docs_url: str = Field(default="http://localhost:8000/docs",
                          description="Docs URL", alias="DOCS_URL")
    pgadmin_url: str = Field(
        default="http://localhost:5555", description="PgAdmin URL", alias="PGADMIN_URL")
    file_storage_url: str = Field(
        default="http://localhost:9001", description="File Storage URL", alias="FILE_STORAGE_URL")
    minio_url: str = Field(default="http://localhost:9000",
                           description="MinIO URL", alias="MINIO_URL")
    redisinsight_url: str = Field(
        default="http://localhost:8001", description="RedisInsight URL", alias="REDISINSIGHT_URL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    def validate_production_secrets(self) -> None:
        """Raise on unsafe defaults when running in production."""
        if self.environment.lower() != "production":
            return
        _INSECURE = {"dev-secret-key-change-in-production", ""}
        if self.jwt_secret in _INSECURE:
            raise ValueError(
                "JWT_SECRET must be set to a strong random value in production"
            )
        if self.minio_secret_key == "minioadmin123":
            import warnings
            warnings.warn(
                "MINIO_SECRET_KEY still uses the default value — "
                "rotate it before exposing the service",
                stacklevel=2,
            )


settings = Settings()
settings.validate_production_secrets()
