"""
Infrastructure URL configuration.
Reads URLs from config.py settings which are loaded from .env file.
"""

from typing import Dict

# Cache for infrastructure URLs to avoid repeated imports
_infrastructure_urls_cache = None

def get_infrastructure_urls() -> Dict[str, str]:
    """Get infrastructure URLs from settings (lazy loaded)"""
    global _infrastructure_urls_cache
    
    if _infrastructure_urls_cache is None:
        from app.core.config import settings
        
        _infrastructure_urls_cache = {
            "database": settings.database_url,
            "api": settings.api_url,
            "docs": settings.docs_url,
            "pgadmin": settings.pgadmin_url,
            "file_storage": settings.file_storage_url,
            "redis": settings.redis_url,
            "minio": settings.minio_url,
            "redisinsight": settings.redisinsight_url
        }
    
    return _infrastructure_urls_cache

def get_current_environment() -> str:
    """Get current environment from settings"""
    from app.core.config import settings
    return getattr(settings, 'environment', 'development')

def get_service_url(service: str) -> str:
    """Get URL for a specific service"""
    urls = get_infrastructure_urls()
    return urls.get(service, "")

# Aliases for backward compatibility
SERVICE_URLS = get_infrastructure_urls()
