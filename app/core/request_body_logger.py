"""
Middleware to log raw request body for specific routes (e.g. for debugging 422 validation).
"""
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)

LOG_BODY_PATHS = frozenset({"/api/v1/restaurants"})


class RequestBodyLoggingMiddleware(BaseHTTPMiddleware):
    """Log raw request body for POST to configured paths so you can see what was sent when validation fails."""

    async def dispatch(self, request: Request, call_next):
        if request.method != "POST" or request.url.path not in LOG_BODY_PATHS:
            return await call_next(request)

        body = await request.body()
        content_type = request.headers.get("content-type", "")
        try:
            body_preview = body.decode("utf-8", errors="replace")
            if len(body_preview) > 2000:
                body_preview = body_preview[:2000] + "... (truncated)"
        except Exception:
            body_preview = repr(body)[:500]

        logger.info(
            "Request body for %s %s: content_type=%s body=%s",
            request.method,
            request.url.path,
            content_type,
            body_preview,
        )

        # Re-expose body so the route can read it (Form/JSON parsing consumes the stream)
        received = [body]

        async def receive():
            if received:
                b = received.pop()
                return {"type": "http.request", "body": b, "more_body": False}
            return {"type": "http.disconnect"}

        request = Request(request.scope, receive)
        return await call_next(request)
