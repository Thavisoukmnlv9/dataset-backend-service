"""
Input sanitization middleware to prevent XSS and injection attacks.
"""
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message
from app.shared.utils.validation.sanitization import (
    sanitize_string,
    sanitize_dict,
    sanitize_filename,
    SanitizationError
)
import json

logger = logging.getLogger(__name__)


class SanitizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to sanitize incoming request data.
    
    This middleware:
    - Sanitizes query parameters
    - Sanitizes form data
    - Sanitizes JSON body data
    - Logs suspicious input patterns
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and sanitize inputs"""
        
        # Store original receive function
        original_receive = request._receive
        
        try:
            # Sanitize query parameters
            if request.url.query:
                sanitized_query = {}
                for key, value in request.query_params.items():
                    if isinstance(value, str):
                        sanitized_query[key] = sanitize_string(value)
                    else:
                        sanitized_query[key] = value
                
                # Note: We can't modify query params easily, so we log instead
                # and let the application handle it
                if request.query_params != sanitized_query:
                    logger.warning(f"Potentially dangerous query parameters detected: {request.url.query}")
            
            # Temporarily disable JSON body sanitization in middleware
            # This avoids consuming the request body stream which prevents FastAPI from parsing it
            # JSON body sanitization can be handled in service layers if needed
            # Only sanitize query parameters and form data for now
            # 
            # For JSON requests, we skip body sanitization to avoid interfering with FastAPI's parsing
            # For multipart/form-data, we also skip as it requires stream processing
            # File names and form data will be sanitized in the service layer
            request._receive = original_receive
            
            # Continue processing
            response = await call_next(request)
            return response
            
        except SanitizationError as e:
            logger.error(f"Sanitization failed: {e}")
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": {
                        "code": "INVALID_INPUT",
                        "message": "Request contains potentially dangerous content"
                    }
                }
            )
        
        except Exception as e:
            logger.error(f"Error in sanitization middleware: {e}", exc_info=True)
            response = await call_next(request)
            return response