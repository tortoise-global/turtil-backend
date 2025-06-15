"""Global exception handlers for the FastAPI application.

This module provides centralized exception handling for consistent error responses.
"""

import logging
import traceback
from typing import Any, Dict

from fastapi import Request, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    BaseAppException,
    BusinessLogicError,
    ConfigurationError,
    ExternalServiceError,
    RateLimitError,
    ResourceConflictError,
    ResourceNotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)


def create_error_response(
    status_code: int,
    error: str,
    detail: str,
    error_code: str = None,
    validation_errors: list = None,
    request_id: str = None,
) -> JSONResponse:
    """Create a standardized error response.

    Args:
        status_code: HTTP status code
        error: Error message
        detail: Detailed error description
        error_code: Application-specific error code
        validation_errors: List of validation errors
        request_id: Request ID for tracking

    Returns:
        JSONResponse with error details
    """
    content = {
        "error": error,
        "detail": detail,
    }

    if error_code:
        content["errorCode"] = error_code

    if validation_errors:
        content["validationErrors"] = validation_errors

    if request_id:
        content["requestId"] = request_id

    return JSONResponse(status_code=status_code, content=content)


async def base_app_exception_handler(
    request: Request, exc: BaseAppException
) -> JSONResponse:
    """Handle custom application exceptions."""
    logger.warning(
        f"Application exception: {exc.error_code} - {exc.message}",
        extra={"details": exc.details, "path": request.url.path},
    )

    status_map = {
        "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
        "AUTHENTICATION_ERROR": status.HTTP_401_UNAUTHORIZED,
        "AUTHORIZATION_ERROR": status.HTTP_403_FORBIDDEN,
        "RESOURCE_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "RESOURCE_CONFLICT": status.HTTP_409_CONFLICT,
        "BUSINESS_LOGIC_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "EXTERNAL_SERVICE_ERROR": status.HTTP_502_BAD_GATEWAY,
        "RATE_LIMIT_ERROR": status.HTTP_429_TOO_MANY_REQUESTS,
        "CONFIGURATION_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    }

    status_code = status_map.get(exc.error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    return create_error_response(
        status_code=status_code,
        error=exc.message,
        detail=str(exc.details) if exc.details else exc.message,
        error_code=exc.error_code,
        request_id=getattr(request.state, "request_id", None),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle FastAPI validation errors."""
    logger.warning(
        f"Validation error: {exc.errors()}", extra={"path": request.url.path}
    )

    validation_errors = []
    for error in exc.errors():
        validation_errors.append(
            {
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
                "input": error.get("input"),
            }
        )

    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error="Validation failed",
        detail="The request contains invalid data",
        error_code="VALIDATION_ERROR",
        validation_errors=validation_errors,
        request_id=getattr(request.state, "request_id", None),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail}", extra={"path": request.url.path}
    )

    return create_error_response(
        status_code=exc.status_code,
        error=exc.detail,
        detail=exc.detail,
        request_id=getattr(request.state, "request_id", None),
    )


async def sqlalchemy_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """Handle SQLAlchemy database errors."""
    logger.error(
        f"Database error: {str(exc)}", extra={"path": request.url.path}, exc_info=True
    )

    if isinstance(exc, IntegrityError):
        return create_error_response(
            status_code=status.HTTP_409_CONFLICT,
            error="Data integrity violation",
            detail="The operation violates database constraints",
            error_code="INTEGRITY_ERROR",
            request_id=getattr(request.state, "request_id", None),
        )

    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error="Database error",
        detail="An error occurred while processing your request",
        error_code="DATABASE_ERROR",
        request_id=getattr(request.state, "request_id", None),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other unhandled exceptions."""
    request_id = getattr(request.state, "request_id", None)

    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        extra={
            "path": request.url.path,
            "request_id": request_id,
            "traceback": traceback.format_exc(),
        },
        exc_info=True,
    )

    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error="Internal server error",
        detail="An unexpected error occurred while processing your request",
        error_code="INTERNAL_ERROR",
        request_id=request_id,
    )


def register_exception_handlers(app):
    """Register all exception handlers with the FastAPI app.

    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(BaseAppException, base_app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
