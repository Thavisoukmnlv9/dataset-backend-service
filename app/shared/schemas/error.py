from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime
from uuid import UUID


class ErrorField(BaseModel):
    """Individual field error information"""
    field: Optional[str] = None
    location: Literal["body", "query", "params"] = "body"
    type: Literal[
        "missing", "invalid_type", "invalid_value", 
        "too_short", "too_long", "pattern_mismatch", "conflict", "not_found",
        "unauthorized", "forbidden", "internal_server_error", "bad_request",
        "rate_limit_exceeded", "authentication_error", "authorization_error",
        "validation_error", "business_logic_error", "resource_unavailable",
        "database_constraint_error", "business_rule_violation",
        "resource_unavailable", "database_constraint_error",
        "business_rule_violation", "resource_unavailable",
        "database_constraint_error", "business_rule_violation",
        "resource_unavailable", "database_constraint_error", "business_rule_violation",
    ] = "invalid_value"
    message: str


class ErrorData(BaseModel):
    """Standardized error data structure"""
    code: str
    message: str
    status_code: int
    fields: List[ErrorField] = Field(default_factory=list)


class MetaData(BaseModel):
    """Metadata for error responses"""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    request_id: Optional[str] = None
    path: Optional[str] = None
    method: Optional[str] = None
    url: Optional[str] = None
    query_params: Optional[dict] = None
    path_params: Optional[dict] = None
    headers: Optional[dict] = None


class StandardErrorResponse(BaseModel):
    """Standardized error response format"""
    success: bool = False
    error: ErrorData
    meta: MetaData

    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat() + "Z"
        }
