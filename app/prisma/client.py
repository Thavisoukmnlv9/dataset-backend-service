"""
Simplified Prisma client with improved connection management.
This replaces the complex manual tracking with Prisma's built-in pooling.
"""
from .generated import Prisma
import logging
from dotenv import load_dotenv
from app.core.config import settings

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Create Prisma client instance
prisma = Prisma(
    datasource={
        "url": settings.database_url
    }
)

db = prisma  # Alias for backward compatibility


async def ensure_connection():
    """
    Ensure Prisma is connected.
    This is a simple wrapper that connects if not already connected.
    Prisma manages connection pooling internally.
    """
    try:
        if not prisma.is_connected():
            await prisma.connect()
            logger.debug("Database connection established")
        return prisma
    except Exception as e:
        logger.error(f"Failed to ensure database connection: {e}", exc_info=True)
        # Re-raise the exception so the caller can handle it
        raise ConnectionError(f"All connection attempts failed: {str(e)}") from e


async def get_db():
    """
    FastAPI dependency for database connection.
    Returns Prisma client that's already connected.
    """
    if not prisma.is_connected():
        await prisma.connect()
    yield prisma


async def connect_db():
    """Connect to the database during startup"""
    try:
        if not prisma.is_connected():
            await prisma.connect()
            logger.info("✅ Database connected successfully with Prisma")
            return True
        return True
    except Exception as e:
        logger.error(f"⚠️  Database connection failed: {e}")
        return False


async def cleanup_all_connections():
    """Cleanup all database connections on shutdown"""
    try:
        if prisma.is_connected():
            await prisma.disconnect()
            logger.info("✅ All database connections cleaned up")
    except Exception as e:
        logger.error(f"⚠️  Error cleaning up database connections: {e}")


async def disconnect_db():
    """Disconnect from the database"""
    try:
        if prisma.is_connected():
            await prisma.disconnect()
            logger.info("✅ Prisma disconnected")
    except Exception as e:
        logger.error(f"⚠️  Prisma disconnection failed: {e}")


# Health check function
async def health_check():
    """Check database health"""
    try:
        if not prisma.is_connected():
            await prisma.connect()
        
        # Simple query to test connection
        await prisma.user.count()
        
        return {
            "status": "healthy",
            "connected": prisma.is_connected()
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "connected": False,
            "error": str(e)
        }

