"""Input validation and sanitization utilities.

This module provides comprehensive input validation and sanitization for security.
"""

import html
import logging
import re
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from email_validator import EmailNotValidError, validate_email
from pydantic import Field, validator

from app.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class ValidationRules:
    """Common validation rules and patterns."""

    # Regex patterns
    PHONE_PATTERN = re.compile(r"^\+?[\d\s\-\(\)]{10,15}$")
    USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\.]{3,30}$")
    PASSWORD_PATTERN = re.compile(
        r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
    )
    NAME_PATTERN = re.compile(
        r"^[a-zA-Z\s\u0900-\u097F\u0980-\u09FF]{2,100}$"
    )  # Include Hindi/Bengali
    CODE_PATTERN = re.compile(r"^[A-Z0-9]{3,10}$")

    # SQL injection patterns to detect
    SQL_INJECTION_PATTERNS = [
        r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)",
        r"(--|#|/\*|\*/)",
        r"(\band\b|\bor\b).*(\b=\b|\blike\b)",
        r"(\'|\").*(\bor\b|\band\b)",
    ]

    # XSS patterns to detect
    XSS_PATTERNS = [
        r"<script.*?>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe.*?>",
        r"<object.*?>",
        r"<embed.*?>",
    ]

    @classmethod
    def compile_patterns(cls):
        """Compile regex patterns for better performance."""
        cls.SQL_INJECTION_REGEX = [
            re.compile(pattern, re.IGNORECASE) for pattern in cls.SQL_INJECTION_PATTERNS
        ]
        cls.XSS_REGEX = [
            re.compile(pattern, re.IGNORECASE) for pattern in cls.XSS_PATTERNS
        ]


# Compile patterns on module load
ValidationRules.compile_patterns()


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """Sanitize string input for security.

    Args:
        value: Input string
        max_length: Maximum allowed length

    Returns:
        Sanitized string

    Raises:
        ValidationError: If input is invalid or potentially malicious
    """
    if not isinstance(value, str):
        raise ValidationError("Input must be a string")

    # Check length
    if len(value) > max_length:
        raise ValidationError(f"Input exceeds maximum length of {max_length}")

    # Check for SQL injection
    for pattern in ValidationRules.SQL_INJECTION_REGEX:
        if pattern.search(value):
            logger.warning(
                "Potential SQL injection attempt detected: %s...", value[:50]
            )
            raise ValidationError("Input contains potentially malicious content")

    # Check for XSS
    for pattern in ValidationRules.XSS_REGEX:
        if pattern.search(value):
            logger.warning("Potential XSS attempt detected: %s...", value[:50])
            raise ValidationError("Input contains potentially malicious content")

    # HTML escape
    sanitized = html.escape(value.strip())

    return sanitized


def validate_email_address(email: str) -> str:
    """Validate and normalize email address.

    Args:
        email: Email address to validate

    Returns:
        Normalized email address

    Raises:
        ValidationError: If email is invalid
    """
    try:
        sanitized_email = sanitize_string(email, 254)  # RFC 5321 limit
        validated_email = validate_email(sanitized_email)
        return validated_email.email.lower()
    except EmailNotValidError as e:
        raise ValidationError(f"Invalid email address: {str(e)}")


def validate_phone_number(phone: str) -> str:
    """Validate phone number format.

    Args:
        phone: Phone number to validate

    Returns:
        Sanitized phone number

    Raises:
        ValidationError: If phone number is invalid
    """
    sanitized_phone = sanitize_string(phone, 20)

    if not ValidationRules.PHONE_PATTERN.match(sanitized_phone):
        raise ValidationError("Invalid phone number format")

    return sanitized_phone


def validate_username(username: str) -> str:
    """Validate username format.

    Args:
        username: Username to validate

    Returns:
        Sanitized username

    Raises:
        ValidationError: If username is invalid
    """
    sanitized_username = sanitize_string(username, 30)

    if not ValidationRules.USERNAME_PATTERN.match(sanitized_username):
        raise ValidationError(
            "Username must be 3-30 characters and contain only letters, numbers, dots, and underscores"
        )

    return sanitized_username.lower()


def validate_password(password: str) -> str:
    """Validate password strength.

    Args:
        password: Password to validate

    Returns:
        Original password if valid

    Raises:
        ValidationError: If password is weak
    """
    if not isinstance(password, str):
        raise ValidationError("Password must be a string")

    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long")

    if len(password) > 128:
        raise ValidationError("Password must not exceed 128 characters")

    if not ValidationRules.PASSWORD_PATTERN.match(password):
        raise ValidationError(
            "Password must contain at least one uppercase letter, one lowercase letter, "
            "one digit, and one special character"
        )

    return password


def validate_name(name: str) -> str:
    """Validate person name format.

    Args:
        name: Name to validate

    Returns:
        Sanitized name

    Raises:
        ValidationError: If name is invalid
    """
    sanitized_name = sanitize_string(name, 100)

    if not ValidationRules.NAME_PATTERN.match(sanitized_name):
        raise ValidationError(
            "Name must be 2-100 characters and contain only letters, spaces, "
            "and supported regional characters"
        )

    return sanitized_name.title()


def validate_code(code: str) -> str:
    """Validate code format (subject codes, etc.).

    Args:
        code: Code to validate

    Returns:
        Sanitized code

    Raises:
        ValidationError: If code is invalid
    """
    sanitized_code = sanitize_string(code, 10)

    if not ValidationRules.CODE_PATTERN.match(sanitized_code):
        raise ValidationError(
            "Code must be 3-10 characters and contain only uppercase letters and numbers"
        )

    return sanitized_code.upper()


def validate_uuid(uuid_str: str) -> UUID:
    """Validate UUID format.

    Args:
        uuid_str: UUID string to validate

    Returns:
        UUID object

    Raises:
        ValidationError: If UUID is invalid
    """
    try:
        return UUID(uuid_str)
    except ValueError:
        raise ValidationError("Invalid UUID format")


def validate_positive_integer(value: int, max_value: int = None) -> int:
    """Validate positive integer.

    Args:
        value: Integer to validate
        max_value: Maximum allowed value

    Returns:
        Validated integer

    Raises:
        ValidationError: If value is invalid
    """
    if not isinstance(value, int):
        raise ValidationError("Value must be an integer")

    if value <= 0:
        raise ValidationError("Value must be positive")

    if max_value and value > max_value:
        raise ValidationError(f"Value must not exceed {max_value}")

    return value


def validate_json_safe(data: Any) -> Any:
    """Validate that data is JSON-safe and doesn't contain malicious content.

    Args:
        data: Data to validate

    Returns:
        Validated data

    Raises:
        ValidationError: If data contains unsafe content
    """
    if isinstance(data, str):
        return sanitize_string(data)
    elif isinstance(data, dict):
        return {key: validate_json_safe(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [validate_json_safe(item) for item in data]
    elif isinstance(data, (int, float, bool)) or data is None:
        return data
    else:
        raise ValidationError(f"Unsupported data type: {type(data)}")


class SecureBaseModel:
    """Base class for models with built-in validation and sanitization."""

    @validator("*", pre=True)
    def sanitize_strings(cls, v):
        """Automatically sanitize string fields."""
        if isinstance(v, str):
            return sanitize_string(v)
        return v

    @validator("email", pre=True)
    def validate_email_field(cls, v):
        """Validate email fields."""
        if v:
            return validate_email_address(v)
        return v

    @validator("phone", pre=True)
    def validate_phone_field(cls, v):
        """Validate phone fields."""
        if v:
            return validate_phone_number(v)
        return v

    @validator("username", pre=True)
    def validate_username_field(cls, v):
        """Validate username fields."""
        if v:
            return validate_username(v)
        return v

    @validator("password", pre=True)
    def validate_password_field(cls, v):
        """Validate password fields."""
        if v:
            return validate_password(v)
        return v


def create_secure_field(field_type: str, **kwargs):
    """Create a Pydantic Field with security validation.

    Args:
        field_type: Type of field (email, phone, username, etc.)
        **kwargs: Additional Field parameters

    Returns:
        Pydantic Field with validation
    """
    validators = {
        "email": [validate_email_address],
        "phone": [validate_phone_number],
        "username": [validate_username],
        "password": [validate_password],
        "name": [validate_name],
        "code": [validate_code],
    }

    if field_type in validators:
        kwargs["validators"] = validators[field_type]

    return Field(**kwargs)
