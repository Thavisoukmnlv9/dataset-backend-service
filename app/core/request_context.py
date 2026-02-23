"""
Request context middleware for tracking requests
"""
import uuid
import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class RequestContextMiddleware(BaseHTTPMiddleware):
    """Add request ID and logging to all requests"""
    
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        start_time = time.time()
        
        # Log incoming request
        logger.info("Incoming request", extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host if request.client else None
        })
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Log response
            logger.info("Request completed", extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2)
            })
            
            response.headers["X-Request-ID"] = request_id
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error("Request failed", extra={
                "request_id": request_id,
                "error": str(e),
                "duration_ms": round(duration * 1000, 2)
            }, exc_info=True)
            raise

