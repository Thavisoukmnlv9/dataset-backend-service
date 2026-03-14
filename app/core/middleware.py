"""
Middleware configuration.

Registers all ASGI middleware on the FastAPI app in the correct order.
Starlette processes middleware in reverse-registration order, so the
first ``add_middleware`` call becomes the *outermost* layer.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.request_context import RequestContextMiddleware
from app.core.request_body_logger import RequestBodyLoggingMiddleware
from app.core.security_middleware import SecurityHeadersMiddleware
from app.shared.middleware.sanitization_middleware import SanitizationMiddleware
from app.core.config import settings


class TunnelCORSMiddleware(BaseHTTPMiddleware):
    """In development, allow CORS from Cloudflare Quick Tunnel origins (*.trycloudflare.com)."""

    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin") or ""
        if (
            settings.environment.lower() == "development"
            and origin.endswith(".trycloudflare.com")
        ):
            request.state.tunnel_origin = origin
        else:
            request.state.tunnel_origin = None
        response = await call_next(request)
        if getattr(request.state, "tunnel_origin", None):
            response.headers["Access-Control-Allow-Origin"] = request.state.tunnel_origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        return response


def setup_middleware(app: FastAPI):
    """Configure all middleware for the FastAPI app."""
    app.add_middleware(TunnelCORSMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(RequestBodyLoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    cors_origins = settings.cors_origins
    cors_allow_credentials = settings.cors_allow_credentials
    
    # Handle wildcard "*" to allow all origins
    # FastAPI's CORSMiddleware accepts ["*"] to allow all origins
    is_wildcard = (
        cors_origins == ["*"] or 
        (len(cors_origins) == 1 and cors_origins[0] == "*")
    )
    
    if is_wildcard:
        if settings.environment.lower() == "production":
            import warnings
            warnings.warn(
                "CORS_ORIGINS=['*'] is not allowed in production. "
                "Falling back to empty origin list.",
                UserWarning,
            )
            cors_origins = []
        if cors_allow_credentials:
            import logging
            logging.getLogger(__name__).warning(
                "CORS_ORIGINS=['*'] with allow_credentials=True is invalid — "
                "setting allow_credentials=False automatically."
            )
        cors_allow_credentials = False
        cors_origins = cors_origins if cors_origins != ["*"] or settings.environment.lower() == "production" else ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
        expose_headers=["X-Request-ID"],
    )
