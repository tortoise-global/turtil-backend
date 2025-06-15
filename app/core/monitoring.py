"""Production monitoring and logging utilities.

This module provides comprehensive monitoring, logging, and metrics collection.
"""

import json
import logging
import time
import uuid
from contextlib import contextmanager
from functools import wraps
from typing import Any, Dict, Optional

from fastapi import Request, Response
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.core.config import settings

# Performance metrics storage
metrics = {
    "requests": {"count": 0, "total_time": 0.0},
    "database": {"queries": 0, "total_time": 0.0},
    "errors": {"count": 0},
    "auth": {"logins": 0, "failures": 0},
}


class StructuredLogger:
    """Structured logging for better monitoring and debugging."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.request_id = None

    def set_request_context(self, request_id: str, user_id: str = None):
        """Set request context for logging."""
        self.request_id = request_id
        self.user_id = user_id

    def _log(self, level: str, message: str, **kwargs):
        """Log with structured format."""
        log_data = {
            "timestamp": time.time(),
            "level": level,
            "message": message,
            "request_id": self.request_id,
            "user_id": getattr(self, "user_id", None),
            **kwargs,
        }

        # Remove None values
        log_data = {k: v for k, v in log_data.items() if v is not None}

        if settings.ENVIRONMENT == "production":
            # JSON format for production
            getattr(self.logger, level.lower())(json.dumps(log_data))
        else:
            # Human-readable format for development
            extra_info = " | ".join(
                f"{k}={v}" for k, v in kwargs.items() if v is not None
            )
            log_msg = f"{message}"
            if extra_info:
                log_msg += f" | {extra_info}"
            getattr(self.logger, level.lower())(log_msg)

    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message."""
        metrics["errors"]["count"] += 1
        self._log("ERROR", message, **kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log("DEBUG", message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message."""
        metrics["errors"]["count"] += 1
        self._log("CRITICAL", message, **kwargs)


class PerformanceMonitor:
    """Monitor application performance metrics."""

    @staticmethod
    def record_request(duration: float, status_code: int, endpoint: str):
        """Record request metrics."""
        metrics["requests"]["count"] += 1
        metrics["requests"]["total_time"] += duration

        if status_code >= 400:
            metrics["errors"]["count"] += 1

    @staticmethod
    def record_database_query(duration: float):
        """Record database query metrics."""
        metrics["database"]["queries"] += 1
        metrics["database"]["total_time"] += duration

    @staticmethod
    def record_auth_event(event_type: str, success: bool):
        """Record authentication metrics."""
        if event_type == "login":
            if success:
                metrics["auth"]["logins"] += 1
            else:
                metrics["auth"]["failures"] += 1

    @staticmethod
    def get_metrics() -> Dict[str, Any]:
        """Get current metrics."""
        return {
            "requests": {
                "total": metrics["requests"]["count"],
                "average_duration": (
                    metrics["requests"]["total_time"] / metrics["requests"]["count"]
                    if metrics["requests"]["count"] > 0
                    else 0
                ),
            },
            "database": {
                "total_queries": metrics["database"]["queries"],
                "average_duration": (
                    metrics["database"]["total_time"] / metrics["database"]["queries"]
                    if metrics["database"]["queries"] > 0
                    else 0
                ),
            },
            "errors": {
                "total": metrics["errors"]["count"],
            },
            "auth": {
                "successful_logins": metrics["auth"]["logins"],
                "failed_logins": metrics["auth"]["failures"],
                "failure_rate": (
                    metrics["auth"]["failures"]
                    / (metrics["auth"]["logins"] + metrics["auth"]["failures"])
                    if (metrics["auth"]["logins"] + metrics["auth"]["failures"]) > 0
                    else 0
                ),
            },
        }


def setup_database_monitoring():
    """Setup database query monitoring."""

    @event.listens_for(Engine, "before_cursor_execute")
    def receive_before_cursor_execute(
        conn, cursor, statement, parameters, context, executemany
    ):
        context._query_start_time = time.time()

    @event.listens_for(Engine, "after_cursor_execute")
    def receive_after_cursor_execute(
        conn, cursor, statement, parameters, context, executemany
    ):
        if hasattr(context, "_query_start_time"):
            duration = time.time() - context._query_start_time
            PerformanceMonitor.record_database_query(duration)

            # Log slow queries
            if duration > 1.0:  # Queries taking more than 1 second
                logger = StructuredLogger("database.slow_query")
                logger.warning(
                    "Slow database query detected",
                    duration=duration,
                    statement=statement[:200],  # First 200 chars
                )


async def request_monitoring_middleware(request: Request, call_next):
    """Middleware for request monitoring and logging."""
    # Generate request ID
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    # Setup logging context
    logger = StructuredLogger("request")
    logger.set_request_context(request_id)

    start_time = time.time()

    # Log request start
    logger.info(
        "Request started",
        method=request.method,
        path=request.url.path,
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = time.time() - start_time

    # Record metrics
    PerformanceMonitor.record_request(duration, response.status_code, request.url.path)

    # Log request completion
    logger.info(
        "Request completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration=duration,
    )

    # Add headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = str(duration)

    return response


def monitor_function(operation_name: str):
    """Decorator to monitor function performance."""

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = StructuredLogger(f"operation.{operation_name}")
            start_time = time.time()

            try:
                logger.info(
                    "%s started", operation_name, extra={"function": func.__name__}
                )
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(
                    "%s completed successfully",
                    operation_name,
                    extra={
                        "function": func.__name__,
                        "duration": duration,
                    },
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    "%s failed",
                    operation_name,
                    extra={
                        "function": func.__name__,
                        "duration": duration,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = StructuredLogger(f"operation.{operation_name}")
            start_time = time.time()

            try:
                logger.info(
                    "%s started", operation_name, extra={"function": func.__name__}
                )
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(
                    f"{operation_name} completed successfully",
                    function=func.__name__,
                    duration=duration,
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"{operation_name} failed",
                    function=func.__name__,
                    duration=duration,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise

        # Return appropriate wrapper based on function type
        if hasattr(func, "__call__") and hasattr(func, "__await__"):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


@contextmanager
def operation_context(operation_name: str, **context_data):
    """Context manager for monitoring operations."""
    logger = StructuredLogger(f"operation.{operation_name}")
    start_time = time.time()

    try:
        logger.info("%s started", operation_name, extra=context_data)
        yield logger
        duration = time.time() - start_time
        logger.info(
            "%s completed", operation_name, extra={"duration": duration, **context_data}
        )
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"{operation_name} failed",
            duration=duration,
            error=str(e),
            error_type=type(e).__name__,
            **context_data,
        )
        raise


class SecurityLogger:
    """Specialized logger for security events."""

    def __init__(self):
        self.logger = StructuredLogger("security")

    def log_authentication_attempt(self, username: str, success: bool, ip: str = None):
        """Log authentication attempt."""
        PerformanceMonitor.record_auth_event("login", success)

        self.logger.info(
            "Authentication attempt",
            username=username,
            success=success,
            ip=ip,
            event_type="auth_attempt",
        )

    def log_authorization_failure(self, user_id: str, resource: str, action: str):
        """Log authorization failure."""
        self.logger.warning(
            "Authorization denied",
            user_id=user_id,
            resource=resource,
            action=action,
            event_type="auth_failure",
        )

    def log_suspicious_activity(
        self, description: str, ip: str = None, user_id: str = None
    ):
        """Log suspicious activity."""
        self.logger.warning(
            "Suspicious activity detected",
            description=description,
            ip=ip,
            user_id=user_id,
            event_type="suspicious_activity",
        )

    def log_data_access(self, user_id: str, resource: str, action: str):
        """Log data access for audit trail."""
        self.logger.info(
            "Data access",
            user_id=user_id,
            resource=resource,
            action=action,
            event_type="data_access",
        )


# Global instances
security_logger = SecurityLogger()


def get_health_status() -> Dict[str, Any]:
    """Get application health status."""
    metrics_data = PerformanceMonitor.get_metrics()

    # Determine health based on metrics
    health_status = "healthy"
    if metrics_data["errors"]["total"] > 100:  # Too many errors
        health_status = "unhealthy"
    elif metrics_data["requests"]["average_duration"] > 2.0:  # Too slow
        health_status = "degraded"

    return {
        "status": health_status,
        "timestamp": time.time(),
        "metrics": metrics_data,
        "environment": settings.ENVIRONMENT,
        "version": settings.VERSION,
    }
