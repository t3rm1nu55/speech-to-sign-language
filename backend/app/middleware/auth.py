"""
Authentication middleware
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    """
    Simple API Key authentication middleware
    Can be extended for JWT, OAuth, etc.
    """

    def __init__(self, app):
        super().__init__(app)
        self.exempt_paths = [
            "/",
            "/api/docs",
            "/api/redoc",
            "/openapi.json",
            "/api/v1/health",
            "/api/v1/health/ready",
            "/api/v1/health/live"
        ]

    async def dispatch(self, request: Request, call_next):
        # Skip auth for exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        # Skip if auth is disabled
        if not settings.API_KEY_ENABLED:
            return await call_next(request)

        # Check for API key
        api_key = request.headers.get(settings.API_KEY_HEADER)

        if not api_key:
            logger.warning(f"Missing API key for request: {request.url.path}")
            return JSONResponse(
                status_code=401,
                content={"error": "Missing API key"}
            )

        # Validate API key (in production, check against database)
        # For now, just check if it exists
        if len(api_key) < 10:
            logger.warning(f"Invalid API key for request: {request.url.path}")
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid API key"}
            )

        # Add user info to request state if needed
        request.state.api_key = api_key

        response = await call_next(request)
        return response
