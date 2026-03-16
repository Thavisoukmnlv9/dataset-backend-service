"""
Middleware configuration.

Registers all ASGI middleware on the FastAPI app in the correct order.
Starlette processes middleware in reverse-registration order, so the
first ``add_middleware`` call becomes the *outermost* layer.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.request_context import RequestContextMiddleware
from app.core.request_body_logger import RequestBodyLoggingMiddleware
from app.core.security_middleware import SecurityHeadersMiddleware
from app.shared.middleware.sanitization_middleware import SanitizationMiddleware
from app.core.config import settings


def setup_middleware(app: FastAPI):
    """Configure all middleware for the FastAPI app.
    Order (last added = outermost): CORS -> Security -> BodyLogging -> RequestContext -> Sanitization -> app.
    """
    app.add_middleware(SanitizationMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(RequestBodyLoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    cors_origins = list(settings.cors_origins) if settings.cors_origins else []
    cors_allow_credentials = settings.cors_allow_credentials
    is_production = settings.environment.strip().lower() == "production"
    is_wildcard = (
        cors_origins == ["*"] or (len(cors_origins) == 1 and cors_origins[0] == "*")
    )

    if is_wildcard:
        if is_production:
            import warnings
            warnings.warn(
                "CORS_ORIGINS=['*'] is not allowed in production. Using empty origin list.",
                UserWarning,
            )
            cors_origins = []
        if cors_allow_credentials:
            import logging
            logging.getLogger(__name__).warning(
                "CORS_ORIGINS=['*'] with allow_credentials=True is invalid — setting allow_credentials=False."
            )
        cors_allow_credentials = False

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
        expose_headers=["X-Request-ID"],
    )