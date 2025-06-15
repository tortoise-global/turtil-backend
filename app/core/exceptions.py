"""Custom exception classes for the application.

This module provides custom exceptions for better error handling and user feedback.
"""

from typing import Any, Dict, Optional


class BaseAppException(Exception):
    """Base exception class for application-specific errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(BaseAppException):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str = "Validation failed",
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if field:
            error_details["field"] = field
        if value is not None:
            error_details["value"] = str(value)

        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=error_details,
        )


class AuthenticationError(BaseAppException):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            details=details,
        )


class AuthorizationError(BaseAppException):
    """Raised when authorization fails."""

    def __init__(
        self,
        message: str = "Access denied",
        required_role: Optional[str] = None,
        current_role: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if required_role:
            error_details["required_role"] = required_role
        if current_role:
            error_details["current_role"] = current_role

        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            details=error_details,
        )


class ResourceNotFoundError(BaseAppException):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        resource_type: str = "Resource",
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"{resource_type} not found"
        if resource_id:
            message += f" with ID: {resource_id}"

        error_details = details or {}
        if resource_id:
            error_details["resource_id"] = resource_id
        error_details["resource_type"] = resource_type

        super().__init__(
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            details=error_details,
        )


class ResourceConflictError(BaseAppException):
    """Raised when a resource conflict occurs."""

    def __init__(
        self,
        message: str = "Resource conflict",
        resource_type: Optional[str] = None,
        conflicting_field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if resource_type:
            error_details["resource_type"] = resource_type
        if conflicting_field:
            error_details["conflicting_field"] = conflicting_field

        super().__init__(
            message=message,
            error_code="RESOURCE_CONFLICT",
            details=error_details,
        )


class BusinessLogicError(BaseAppException):
    """Raised when business logic rules are violated."""

    def __init__(
        self,
        message: str,
        rule: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if rule:
            error_details["violated_rule"] = rule

        super().__init__(
            message=message,
            error_code="BUSINESS_LOGIC_ERROR",
            details=error_details,
        )


class ExternalServiceError(BaseAppException):
    """Raised when external service calls fail."""

    def __init__(
        self,
        service_name: str,
        message: str = "External service error",
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        error_details["service_name"] = service_name
        if status_code:
            error_details["status_code"] = status_code

        super().__init__(
            message=f"{service_name}: {message}",
            error_code="EXTERNAL_SERVICE_ERROR",
            details=error_details,
        )


class RateLimitError(BaseAppException):
    """Raised when rate limits are exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        limit: Optional[int] = None,
        window: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if limit:
            error_details["rate_limit"] = limit
        if window:
            error_details["time_window"] = window

        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            details=error_details,
        )


class ConfigurationError(BaseAppException):
    """Raised when configuration is invalid or missing."""

    def __init__(
        self,
        config_key: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        msg = message or f"Invalid or missing configuration: {config_key}"
        error_details = details or {}
        error_details["config_key"] = config_key

        super().__init__(
            message=msg,
            error_code="CONFIGURATION_ERROR",
            details=error_details,
        )
