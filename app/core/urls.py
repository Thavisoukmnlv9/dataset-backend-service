"""
URL routing configuration.
"""
import importlib
import logging
from fastapi import FastAPI
from typing import List, Tuple
from app.core.settings import SERVICES_TO_LOAD, API_ENDPOINTS

logger = logging.getLogger(__name__)

_ALLOWED_MODULES = frozenset(s.import_path for s in SERVICES_TO_LOAD)


def load_service(app: FastAPI, service_name: str, import_path: str, router_name: str = "router") -> bool:
    """Load a service router, restricted to the allow-list in SERVICES_TO_LOAD."""
    if import_path not in _ALLOWED_MODULES:
        logger.error("Refused to load unlisted module: %s", import_path)
        return False
    try:
        module = importlib.import_module(import_path)
        router = getattr(module, router_name)
        app.include_router(router, prefix="/api/v1")
        app.include_router(router)
        logger.info("%s service routes loaded", service_name)
        return True
    except Exception as e:
        logger.error("Failed to load %s routes: %s", service_name, e)
        return False


def register_services(app: FastAPI) -> Tuple[List[str], List[str]]:
    """Register all services with the FastAPI app."""
    loaded_services: List[str] = []
    failed_services: List[str] = []

    for service in SERVICES_TO_LOAD:
        if not service.enabled:
            logger.info("Skipping disabled service: %s", service.name)
            continue
        if load_service(app, service.name, service.import_path, service.router_name):
            loaded_services.append(service.name)
        else:
            failed_services.append(service.name)

    return loaded_services, failed_services

def register_core_routes(app: FastAPI, loaded_services: List[str], failed_services: List[str]):
    """Register core application routes"""
    
    @app.get("/")
    async def root():
        """Root endpoint with API information."""
        return {
            "message": "Welcome to dataset Tourism Middleware API",
            "version": "2.1.0",
            "architecture": "Modular Monolith - Phase 1 Focus",
            "phase": "Phase 1 - Core Tourism Services",
            "loaded_services": loaded_services,
            "failed_services": failed_services,
            "total_services": len([s for s in SERVICES_TO_LOAD if s.enabled]),
            "success_rate": f"{len(loaded_services)}/{len([s for s in SERVICES_TO_LOAD if s.enabled])}",
            "docs": "/docs",
            "health": "/health"
        }

    @app.get("/health")
    async def health_check():
        """Health check endpoint for monitoring."""
        from datetime import datetime, UTC

        return {
            "status": "healthy",
            "service": "dataset-tourism-middleware",
            "version": "2.1.0",
            "loaded_services": len(loaded_services),
            "failed_services": len(failed_services),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    @app.get("/api/v1/health")
    async def api_health_check():
        """API health check endpoint."""
        return {
            "status": "healthy",
            "service": "dataset-tourism-middleware",
            "version": "2.1.0",
            "loaded_services": loaded_services,
            "failed_services": failed_services,
            "endpoints": API_ENDPOINTS
        }
