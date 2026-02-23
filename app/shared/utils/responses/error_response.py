from typing import List, Optional, Dict, Any
from datetime import UTC, datetime
import uuid
from fastapi import Request
from app.shared.schemas.error import StandardErrorResponse, ErrorData, ErrorField, MetaData


def create_standard_error_response(
    error_code: str,
    message: str,
    status_code: int,
    fields: Optional[List[Dict[str, Any]]] = None,
    request: Optional[Request] = None,
    request_id: Optional[str] = None
) -> StandardErrorResponse:
    """
    Create a standardized error response following the new unified format.
    
    Args:
        error_code: Error code (e.g., "VALIDATION_ERROR", "NOT_FOUND")
        message: Human-readable error message
        status_code: HTTP status code
        fields: List of field-specific errors (optional)
        request: FastAPI Request object for metadata (optional)
        request_id: Request ID (optional, will generate if not provided)
    
    Returns:
        StandardErrorResponse: Standardized error response
    """
    # Convert field errors to ErrorField objects
    error_fields = []
    if fields:
        for field in fields:
            error_fields.append(ErrorField(
                field=field.get("field"),
                location=field.get("location", "body"),
                type=field.get("type", "invalid_value"),
                message=field.get("message", "Invalid value")
            ))
    
    # Create error data
    error_data = ErrorData(
        code=error_code,
        message=message,
        status_code=status_code,
        fields=error_fields
    )
    
    # Convert headers to dict for proper JSON serialization
    headers_dict = None
    if request and request.headers:
        # Convert Starlette Headers to a regular dict, handling any special characters
        headers_dict = {}
        for key, value in request.headers.items():
            # Store headers as-is (nginx may pass unusual values)
            headers_dict[key.lower()] = value
    
    # Create metadata
    meta_data = MetaData(
        timestamp=datetime.now(UTC).isoformat() + "Z",
        request_id=request_id or str(uuid.uuid4()),
        path=request.url.path if request else None,
        method=request.method if request else None,
        url=str(request.url) if request else None,
        query_params=dict(request.query_params) if request and request.query_params else None,
        path_params=dict(request.path_params) if request and request.path_params else None,
        headers=headers_dict,
    )
    return StandardErrorResponse(
        success=False,
        error=error_data,
        meta=meta_data
    )


def create_validation_error_response(
    validation_errors: List[Dict[str, Any]],
    request: Optional[Request] = None,
    request_id: Optional[str] = None
) -> StandardErrorResponse:
    """
    Create a standardized validation error response.
    
    Args:
        validation_errors: List of validation errors from Pydantic/FastAPI
        request: FastAPI Request object (optional)
        request_id: Request ID (optional)
    
    Returns:
        StandardErrorResponse: Standardized validation error response
    """
    fields = []
    for error in validation_errors:
        field_path = " -> ".join(str(loc) for loc in error.get("loc", []))
        error_type = error.get("type", "invalid_value")
        
        # Map Pydantic error types to our standard types
        type_mapping = {
            "missing": "missing",
            "type_error": "invalid_type",
            "value_error": "invalid_value",
            "string_too_short": "too_short",
            "string_too_long": "too_long",
            "string_pattern_mismatch": "pattern_mismatch"
        }
        
        mapped_type = type_mapping.get(error_type, "invalid_value")
        
        fields.append({
            "field": field_path,
            "location": "body",
            "type": mapped_type,
            "message": error.get("msg", "Invalid value")
        })
    
    return create_standard_error_response(
        error_code="VALIDATION_ERROR",
        message="Invalid input data",
        status_code=422,
        fields=fields,
        request=request,
        request_id=request_id
    )


def create_http_error_response(
    status_code: int,
    message: str,
    request: Optional[Request] = None,
    request_id: Optional[str] = None
) -> StandardErrorResponse:
    """
    Create a standardized HTTP error response.
    
    Args:
        status_code: HTTP status code
        message: Error message
        request: FastAPI Request object (optional)
        request_id: Request ID (optional)
    
    Returns:
        StandardErrorResponse: Standardized HTTP error response
    """
    # Map status codes to error codes
    error_code_mapping = {
        400: "BAD_REQUEST",
        401: "AUTHENTICATION_ERROR",
        403: "AUTHORIZATION_ERROR",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_SERVER_ERROR"
    }
    
    error_code = error_code_mapping.get(status_code, "HTTP_ERROR")
    
    return create_standard_error_response(
        error_code=error_code,
        message=message,
        status_code=status_code,
        request=request,
        request_id=request_id
    )


def create_business_logic_error_response(
    error_code: str,
    message: str,
    status_code: int = 400,
    fields: Optional[List[Dict[str, Any]]] = None,
    request: Optional[Request] = None,
    request_id: Optional[str] = None
) -> StandardErrorResponse:
    """
    Create a standardized business logic error response.
    
    Args:
        error_code: Business logic error code
        message: Error message
        status_code: HTTP status code (default: 400)
        fields: Field-specific errors (optional)
        request: FastAPI Request object (optional)
        request_id: Request ID (optional)
    
    Returns:
        StandardErrorResponse: Standardized business logic error response
    """


    return create_standard_error_response(
        error_code=error_code,
        message=message,
        status_code=status_code,
        fields=fields,
        request=request,
        request_id=request_id
    )
