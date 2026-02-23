from datetime import datetime, timedelta, UTC
from typing import Dict, Any, Optional
import logging
from app.prisma import prisma

logger = logging.getLogger(__name__)

# Rate limit configurations
RATE_LIMITS = {
    "forgot_password": {"limit": 5, "window_hours": 1},  # 5 requests per hour
    "verify_otp": {"limit": 10, "window_hours": 1},      # 10 requests per hour
    "reset_password": {"limit": 5, "window_hours": 1},   # 5 requests per hour
    "resend_otp": {"limit": 3, "window_hours": 1},       # 3 requests per hour
}


class RateLimitService:
    """Rate limiting service for auth endpoints"""
    
    @staticmethod
    def get_identifier(ip_address: str, email: str = None) -> str:
        """Generate rate limit identifier from IP and email."""
        if email:
            return f"{ip_address}:{email}"
        return ip_address
    
    @staticmethod
    async def check_rate_limit(
        identifier: str, 
        endpoint: str, 
        ip_address: str
    ) -> Dict[str, Any]:
        """Check if request is within rate limits."""
        try:
            
            # Get rate limit config for endpoint
            config = RATE_LIMITS.get(endpoint, {"limit": 5, "window_hours": 1})
            limit = config["limit"]
            window_hours = config["window_hours"]
            
            # Calculate window start time
            window_start = datetime.now(UTC) - timedelta(hours=window_hours)
            
            # Find existing rate limit records
            existing_records = await prisma.ratelimit.find_many(
                where={
                    "identifier": identifier,
                    "endpoint": endpoint,
                    "window_start": {"gte": window_start}
                }
            )
            
            # Calculate current count
            current_count = sum(record.count for record in existing_records)
            
            if current_count >= limit:
                return {
                    "allowed": False,
                    "limit": limit,
                    "remaining": 0,
                    "reset_time": window_start + timedelta(hours=window_hours)
                }
            
            # Record this request
            try:
                await prisma.ratelimit.create(
                    data={
                        "identifier": identifier,
                        "endpoint": endpoint,
                        "count": 1,
                        "window_start": datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
                    }
                )
            except Exception as create_error:
                if "Unique constraint failed" in str(create_error):
                    await prisma.ratelimit.update_many(
                        where={
                            "identifier": identifier,
                            "endpoint": endpoint,
                            "window_start": datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
                        },
                        data={"count": {"increment": 1}}
                    )
                else:
                    raise
            
            return {
                "allowed": True,
                "limit": limit,
                "remaining": limit - current_count - 1,
                "reset_time": window_start + timedelta(hours=window_hours)
            }
            
        except Exception as e:
            logger.error(f"Error checking rate limit for {identifier}: {str(e)}")
            # Fail open - allow request if rate limiting fails
            return {
                "allowed": True,
                "limit": 5,
                "remaining": 5,
                "reset_time": datetime.now(UTC) + timedelta(hours=1)
            }
    
    @staticmethod
    async def cleanup_expired_limits() -> int:
        """Clean up expired rate limit records."""
        try:
            
            # Clean up records older than 24 hours
            cutoff_time = datetime.now(UTC) - timedelta(hours=24)
            result = await prisma.ratelimit.delete_many(
                where={
                    "window_start": {"lt": cutoff_time}
                }
            )
            
            logger.info(f"Cleaned up {result} expired rate limit records")
            return result
            
        except Exception as e:
            logger.error(f"Error cleaning up rate limits: {str(e)}")
            return 0
    
    @staticmethod
    async def get_rate_limit_info(identifier: str, endpoint: str) -> Dict[str, Any]:
        """Get current rate limit information for an identifier."""
        try:
            
            config = RATE_LIMITS.get(endpoint, {"limit": 5, "window_hours": 1})
            limit = config["limit"]
            window_hours = config["window_hours"]
            
            window_start = datetime.now(UTC) - timedelta(hours=window_hours)
            
            existing_records = await prisma.ratelimit.find_many(
                where={
                    "identifier": identifier,
                    "endpoint": endpoint,
                    "window_start": {"gte": window_start}
                }
            )
            
            current_count = sum(record.count for record in existing_records)
            
            return {
                "limit": limit,
                "used": current_count,
                "remaining": max(0, limit - current_count),
                "reset_time": window_start + timedelta(hours=window_hours)
            }
            
        except Exception as e:
            logger.error(f"Error getting rate limit info for {identifier}: {str(e)}")
            return {
                "limit": 5,
                "used": 0,
                "remaining": 5,
                "reset_time": datetime.now(UTC) + timedelta(hours=1)
            }
