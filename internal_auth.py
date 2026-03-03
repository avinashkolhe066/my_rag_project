# internal_auth.py
# Place this file in your Python my_rag_project/ folder
# Then add the middleware to your main.py (see instructions at bottom)

import os
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


class InternalAPIKeyMiddleware(BaseHTTPMiddleware):
    """
    Validates that every incoming request carries the correct
    X-Internal-API-Key header. This prevents anyone from calling
    the Python RAG service directly without going through Node.js.

    Add to main.py:
        from internal_auth import InternalAPIKeyMiddleware
        app.add_middleware(InternalAPIKeyMiddleware)
    """

    # Routes that do NOT require the key (health check only)
    EXEMPT_PATHS = {"/", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        api_key = request.headers.get("X-Internal-API-Key")
        expected = os.getenv("INTERNAL_SECRET")

        if not expected:
            # If INTERNAL_SECRET not set, skip check (dev mode)
            return await call_next(request)

        if api_key != expected:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: Invalid or missing internal API key.",
            )

        return await call_next(request)
