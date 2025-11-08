"""
Rate limiting middleware
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.config import settings
import time
import logging
from collections import defaultdict
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting
    In production, use Redis for distributed rate limiting
    """

    def __init__(self, app):
        super().__init__(app)
        # Store: {ip_address: [(timestamp, count)]}
        self.requests: Dict[str, list] = defaultdict(list)
        self.exempt_paths = [
            "/",
            "/api/docs",
            "/api/redoc",
            "/openapi.json",
            "/api/v1/health",
            "/api/v1/health/ready",
            "/api/v1/health/live"
        ]

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Check for forwarded IP (behind proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Check for real IP
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Use direct connection IP
        if request.client:
            return request.client.host

        return "unknown"

    def _cleanup_old_requests(self, ip: str, current_time: float):
        """Remove requests older than 1 minute"""
        if ip in self.requests:
            self.requests[ip] = [
                (ts, count) for ts, count in self.requests[ip]
                if current_time - ts < 60
            ]

    def _check_rate_limit(self, ip: str) -> Tuple[bool, int]:
        """
        Check if IP has exceeded rate limit
        Returns: (is_allowed, remaining_requests)
        """
        if not settings.RATE_LIMIT_ENABLED:
            return True, settings.RATE_LIMIT_PER_MINUTE

        current_time = time.time()

        # Cleanup old requests
        self._cleanup_old_requests(ip, current_time)

        # Count requests in last minute
        request_count = sum(count for _, count in self.requests[ip])

        # Check limit
        if request_count >= settings.RATE_LIMIT_PER_MINUTE:
            return False, 0

        # Add current request
        self.requests[ip].append((current_time, 1))

        remaining = settings.RATE_LIMIT_PER_MINUTE - request_count - 1
        return True, remaining

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        # Get client IP
        client_ip = self._get_client_ip(request)

        # Check rate limit
        is_allowed, remaining = self._check_rate_limit(client_ip)

        if not is_allowed:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Maximum {settings.RATE_LIMIT_PER_MINUTE} requests per minute"
                },
                headers={
                    "X-RateLimit-Limit": str(settings.RATE_LIMIT_PER_MINUTE),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + 60)
                }
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_PER_MINUTE)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response
