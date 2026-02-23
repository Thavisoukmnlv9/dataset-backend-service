"""
Exception handlers configuration.
Similar to Django's exception handling
"""
import logging
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.shared.utils.responses.error_response import (
    create_standard_error_response,
    create_validation_error_response,
    create_http_error_response
)
from app.shared.exceptions import StandardHTTPException

logger = logging.getLogger(__name__)

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    # Skip validation errors for OPTIONS requests (CORS preflight)
    # These should be handled by CORSMiddleware
    if request.method == "OPTIONS":
        return Response(status_code=200)
    
    logger.error(f"Validation error: {exc}")
    
    # Create standardized validation error response
    error_response = create_validation_error_response(
        validation_errors=exc.errors(),
        request=request
    )
    
    return JSONResponse(
        status_code=422,
        content=error_response.model_dump()
    )

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    # Skip error handling for OPTIONS requests (CORS preflight)
    # These should be handled by CORSMiddleware
    if request.method == "OPTIONS":
        return Response(status_code=200)
    
    logger.error(f"HTTP error: {exc}")
    
    # Handle StandardHTTPException with custom error format
    if isinstance(exc, StandardHTTPException):
        error_response = create_standard_error_response(
            error_code=exc.error_code,
            message=exc.detail,
            status_code=exc.status_code,
            fields=exc.fields,
            request=request,
            request_id=exc.request_id
        )
    else:
        # Handle regular HTTPException
        error_response = create_http_error_response(
            status_code=exc.status_code,
            message=exc.detail,
            request=request
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )

async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unexpected error: {exc}")
    
    # Create standardized internal server error response
    error_response = create_standard_error_response(
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred",
        status_code=500,
        request=request
    )
    
    return JSONResponse(
        status_code=500,
        content=error_response.model_dump()
    )

def setup_exception_handlers(app):
    """Register all exception handlers with the FastAPI app"""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
