from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import time
from typing import Optional

from app.core.auth_manager import auth_manager
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisAuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware with Redis cache integration.
    Provides immediate revocation support and sub-50ms authentication.
    """
    
    def __init__(self, app, excluded_paths: Optional[list] = None):
        super().__init__(app)
        # Paths that don't require authentication
        self.excluded_paths = excluded_paths or [
            "/docs",
            "/redoc", 
            "/openapi.json",
            "/api/v1/cms/auth/login",
            "/api/v1/cms/auth/signup",
            "/api/v1/cms/auth/send-email",
            "/api/v1/cms/auth/verify-email",
            "/health",
            "/",
        ]
    
    async def dispatch(self, request: Request, call_next):
        # Start timing for performance monitoring
        start_time = time.time()
        
        # Check if path requires authentication
        if self._is_excluded_path(request.url.path):
            response = await call_next(request)
            return response
        
        # Extract Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return self._unauthorized_response("Missing or invalid authorization header")
        
        # Extract token
        token = auth_header.replace("Bearer ", "")
        
        try:
            # Verify token with Redis cache integration
            payload = auth_manager.verify_token(token)
            user_id = payload.get("sub")
            
            if not user_id:
                return self._unauthorized_response("Invalid token payload")
            
            # Check if user is blacklisted (immediate revocation)
            if auth_manager.redis.is_available():
                if auth_manager.redis.is_user_blacklisted(user_id):
                    logger.warning(f"Blocked request from blacklisted user: {user_id}")
                    return self._unauthorized_response("Access revoked")
            
            # Add user info to request state for downstream handlers
            request.state.user_id = user_id
            request.state.user_payload = payload
            request.state.auth_time = time.time() - start_time
            
            # Continue with request
            response = await call_next(request)
            
            # Add performance headers
            auth_time_ms = round((time.time() - start_time) * 1000, 2)
            response.headers["X-Auth-Time"] = str(auth_time_ms)
            response.headers["X-Cache-Status"] = "hit" if auth_time_ms < 50 else "miss"
            
            return response
            
        except HTTPException as e:
            logger.warning(f"Authentication failed for path {request.url.path}: {e.detail}")
            return self._unauthorized_response(e.detail)
        except Exception as e:
            logger.error(f"Unexpected auth error: {e}")
            return self._unauthorized_response("Authentication failed")
    
    def _is_excluded_path(self, path: str) -> bool:
        """Check if the path is excluded from authentication."""
        for excluded in self.excluded_paths:
            if path.startswith(excluded):
                return True
        return False
    
    def _unauthorized_response(self, detail: str) -> JSONResponse:
        """Return standardized unauthorized response."""
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "detail": detail,
                "type": "authentication_error",
                "code": "UNAUTHORIZED"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with Redis backend.
    Prevents abuse and ensures fair usage.
    """
    
    def __init__(self, app, calls_per_minute: int = 100):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute
        self.window_size = 60  # 1 minute
    
    async def dispatch(self, request: Request, call_next):
        # Get client identifier (user_id if authenticated, IP otherwise)
        client_id = getattr(request.state, 'user_id', None) or self._get_client_ip(request)
        
        # Check rate limit using Redis
        if auth_manager.redis.is_available():
            if not self._check_rate_limit(client_id):
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Rate limit exceeded",
                        "retry_after": 60
                    }
                )
        
        response = await call_next(request)
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to client host
        return request.client.host if request.client else "unknown"
    
    def _check_rate_limit(self, client_id: str) -> bool:
        """Check if client is within rate limits."""
        try:
            key = f"rate_limit:{client_id}"
            current_time = int(time.time())
            window_start = current_time - self.window_size
            
            # Use Redis sorted set to track requests in time window
            if auth_manager.redis.redis:
                # Remove old entries
                auth_manager.redis.redis.zremrangebyscore(key, 0, window_start)
                
                # Count current requests
                current_count = auth_manager.redis.redis.zcard(key)
                
                if current_count >= self.calls_per_minute:
                    return False
                
                # Add current request
                auth_manager.redis.redis.zadd(key, {str(current_time): current_time})
                auth_manager.redis.redis.expire(key, self.window_size)
                
                return True
            
            # If Redis unavailable, allow request (fail open)
            return True
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return True  # Fail open


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to responses.
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # API-specific headers
        response.headers["X-API-Version"] = settings.VERSION
        response.headers["X-Powered-By"] = f"Turtil-Backend/{settings.VERSION}"
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log requests for monitoring and debugging.
    """
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Get user info if available
        user_id = getattr(request.state, 'user_id', 'anonymous')
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log request details
        logger.info(
            f"{request.method} {request.url.path} - "
            f"User: {user_id} - "
            f"Status: {response.status_code} - "
            f"Time: {round(process_time * 1000, 2)}ms"
        )
        
        # Add timing header
        response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
        
        return response