from fastapi import HTTPException, Request
from typing import Optional, List, Dict, Any
from app.shared.utils.responses.error_response import create_standard_error_response


class StandardHTTPException(HTTPException):
    """
    Custom HTTPException that works with the standardized error format.
    This allows services to raise exceptions that will be properly formatted.
    """
    
    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        fields: Optional[List[Dict[str, Any]]] = None,
        request: Optional[Request] = None,
        request_id: Optional[str] = None
    ):
        super().__init__(status_code=status_code, detail=message)
        self.error_code = error_code
        self.fields = fields or []
        self.request = request
        self.request_id = request_id


def raise_validation_error(
    message: str = "Invalid input data",
    fields: Optional[List[Dict[str, Any]]] = None,
    request: Optional[Request] = None
) -> None:
    """Raise a standardized validation error"""
    raise StandardHTTPException(
        status_code=422,
        error_code="VALIDATION_ERROR",
        message=message,
        fields=fields,
        request=request
    )


def raise_not_found_error(
    message: str = "Resource not found",
    fields: Optional[List[Dict[str, Any]]] = None,
    request: Optional[Request] = None
) -> None:
    """Raise a standardized not found error"""
    raise StandardHTTPException(
        status_code=404,
        error_code="NOT_FOUND",
        message=message,
        fields=fields,
        request=request
    )


def raise_conflict_error(
    message: str = "Resource conflict",
    fields: Optional[List[Dict[str, Any]]] = None,
    request: Optional[Request] = None
) -> None:
    """Raise a standardized conflict error"""
    raise StandardHTTPException(
        status_code=409,
        error_code="CONFLICT",
        message=message,
        fields=fields,
        request=request
    )


def raise_unauthorized_error(
    message: str = "Authentication required",
    request: Optional[Request] = None
) -> None:
    """Raise a standardized unauthorized error"""
    raise StandardHTTPException(
        status_code=401,
        error_code="AUTHENTICATION_ERROR",
        message=message,
        request=request
    )


def raise_forbidden_error(
    message: str = "Insufficient permissions",
    fields: Optional[List[Dict[str, Any]]] = None,
    request: Optional[Request] = None
) -> None:
    """Raise a standardized forbidden error"""
    raise StandardHTTPException(
        status_code=403,
        error_code="AUTHORIZATION_ERROR",
        message=message,
        fields=fields,
        request=request
    )


def raise_business_logic_error(
    error_code: str,
    message: str,
    status_code: int = 400,
    fields: Optional[List[Dict[str, Any]]] = None,
    request: Optional[Request] = None
) -> None:
    """Raise a standardized business logic error"""
    raise StandardHTTPException(
        status_code=status_code,
        error_code=error_code,
        message=message,
        fields=fields,
        request=request
    )
