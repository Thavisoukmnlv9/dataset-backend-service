from typing import Any, Optional, Dict, List
from datetime import UTC, datetime
import uuid
from app.shared.schemas.base import ResponseModel, ErrorResponse, PaginationResponse
from app.shared.utils.responses.error_response import create_standard_error_response

def create_success_response(
    data: Any = None,
    message: str = "Operation successful",
    request_id: Optional[str] = None
) -> ResponseModel:
    """Create a standardized success response"""
    return ResponseModel(
        success=True,
        data=data,
        message=message,
        timestamp=datetime.now(UTC),
        request_id=request_id or str(uuid.uuid4())
    )

def create_error_response(
    error_code: str,
    message: str,
    details: Optional[List[Dict[str, str]]] = None,
    request_id: Optional[str] = None,
    status_code: int = 400,
    request: Optional[Any] = None
) -> ErrorResponse:
    """Create a standardized error response (legacy function for backward compatibility)"""
    # Convert details to fields format for new structure
    fields = []
    if details:
        for detail in details:
            fields.append({
                "field": detail.get("field"),
                "location": "body",
                "type": "invalid_value",
                "message": detail.get("message", "Invalid value")
            })
    
    # Create standard error response
    standard_response = create_standard_error_response(
        error_code=error_code,
        message=message,
        status_code=status_code,
        fields=fields,
        request=request,
        request_id=request_id
    )
    
    # Convert back to legacy format for backward compatibility
    error_data = {
        "code": standard_response.error.code,
        "message": standard_response.error.message,
        "status_code": standard_response.error.status_code
    }
    if standard_response.error.fields:
        error_data["fields"] = [
            {
                "field": field.field,
                "location": field.location,
                "type": field.type,
                "message": field.message
            }
            for field in standard_response.error.fields
        ]
    
    return ErrorResponse(
        success=False,
        error=error_data,
        timestamp=datetime.now(UTC),
        request_id=standard_response.meta.request_id
    )

def create_pagination_response(
    items: List[Any],
    total: int,
    page: int,
    limit: int,
    offset: int
) -> PaginationResponse:
    """Create a pagination response"""
    pages = (total + limit - 1) // limit
    return PaginationResponse(
        page=page,
        limit=limit,
        total=total,
        pages=pages,
        offset=offset,
        has_next=page < pages,
        has_prev=page > 1
    )

def create_list_response(
    items: List[Any],
    total: int,
    page: int,
    limit: int,
    offset: int,
    message: str = "List retrieved successfully",
    request_id: Optional[str] = None
) -> ResponseModel:
    """Create a standardized list response with pagination"""
    pagination = create_pagination_response(items, total, page, limit, offset)
    return create_success_response(
        data={
            "items": items,
            "pagination": pagination
        },
        message=message,
        request_id=request_id
    )
