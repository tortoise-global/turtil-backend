"""Custom middleware for request processing.

This module provides middleware for:
- Rate limiting by client IP
- Input sanitization for security
- Request validation and filtering
"""

import html
import time
from typing import Dict

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware to prevent abuse.
    
    Limits the number of requests per IP address within a time period.
    """
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients: Dict[str, list] = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        current_time = time.time()

        if client_ip not in self.clients:
            self.clients[client_ip] = []

        self.clients[client_ip] = [
            timestamp
            for timestamp in self.clients[client_ip]
            if current_time - timestamp < self.period
        ]

        if len(self.clients[client_ip]) >= self.calls:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
            )

        self.clients[client_ip].append(current_time)
        response = await call_next(request)
        return response


class SanitizeInputMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "PATCH"]:
            if "application/json" in request.headers.get("content-type", ""):
                body = await request.body()
                if body:
                    try:
                        import json

                        data = json.loads(body)
                        sanitized_data = self.sanitize_dict(data)
                        request._body = json.dumps(sanitized_data).encode()
                    except json.JSONDecodeError:
                        pass

        response = await call_next(request)
        return response

    def sanitize_dict(self, data):
        if isinstance(data, dict):
            return {key: self.sanitize_value(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self.sanitize_value(item) for item in data]
        else:
            return self.sanitize_value(data)

    def sanitize_value(self, value):
        if isinstance(value, str):
            return html.escape(value.strip())
        elif isinstance(value, dict):
            return self.sanitize_dict(value)
        elif isinstance(value, list):
            return [self.sanitize_value(item) for item in value]
        else:
            return value
