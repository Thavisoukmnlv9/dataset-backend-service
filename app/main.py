import logging
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.settings import app_settings
from app.core.middleware import setup_middleware
from app.core.exceptions import setup_exception_handlers
from app.core.urls import register_services, register_core_routes

# Configure logging
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events"""
    worker_task = None
    try:
        from app.prisma import connect_db, cleanup_all_connections     
        
        # Startup
        success = await connect_db()
        
        # Display startup information with ASCII art (after loading everything)
        from app.core.startup import startup_display
        loaded_count = getattr(app.state, 'loaded_services_count', 0)
        failed_count = getattr(app.state, 'failed_services_count', 0)
        startup_display.display_full_startup(loaded_services=loaded_count, failed_services=failed_count)
        
        # Log after display (so it doesn't appear above the banner)
        logger.info("Starting up dataset Tourism Middleware API...")
        if success:
            logger.info("Database connected successfully")
        else:
            logger.warning("Database connection failed, but continuing startup...")
        
        # Note: ARQ worker should be started separately using start_worker.py
        logger.info("ARQ worker not started automatically. Use 'python start_worker.py' to start it.")
        
        yield
        
        # Shutdown
        logger.info("Shutting down dataset Tourism Middleware API...")
        
        # ARQ worker is managed separately
        
        await cleanup_all_connections()
        logger.info("Database connections cleaned up successfully")
        
    except Exception as e:
        logger.error(f"Error during startup/shutdown: {e}")
        try:
            if worker_task:
                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass
            from app.prisma import cleanup_all_connections
            await cleanup_all_connections()
        except Exception:
            logger.exception("Cleanup during error handling also failed")
        yield

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    Similar to Django's application factory pattern.
    """
    # Create FastAPI app with settings
    app = FastAPI(
        title=app_settings.title,
        description=app_settings.description,
        version=app_settings.version,
        contact=app_settings.contact,
        license_info=app_settings.license_info,
        lifespan=lifespan,
        redirect_slashes=True,  # Disable automatic trailing slash redirects
    )

    setup_middleware(app)

    # Serve local uploads when storage provider is local
    if (settings.storage_provider or "local").strip().lower() == "local":
        upload_dir = Path(settings.storage_local_base_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        base_url = (settings.storage_local_public_base_url or "/uploads").strip()
        app.mount(base_url, StaticFiles(directory=str(upload_dir)), name="uploads")
    
    # Setup exception handlers
    setup_exception_handlers(app)
    
    # Register services and get status
    loaded_services, failed_services = register_services(app)
    
    # Store service counts in app state for startup display
    app.state.loaded_services_count = len(loaded_services)
    app.state.failed_services_count = len(failed_services)
    
    # Register core routes
    register_core_routes(app, loaded_services, failed_services)
    
    return app

# Create the application instance
app = create_app()