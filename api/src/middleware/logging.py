import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Generate unique request ID
        request_id = str(uuid.uuid4())[:8]  # Short ID

        # Record start time
        start_time = time.time()

        # Log request
        print(f"[{request_id}] --> {request.method} {request.url.path}")

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = round((time.time() - start_time) * 1000, 2)

        # Log response
        print(f"[{request_id}] <-- {response.status_code} ({duration_ms}ms)")

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response
