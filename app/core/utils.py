import re
import secrets
import string
from typing import Any, Dict
from pydantic import BaseModel
from pydantic.alias_generators import to_camel


def snake_to_camel(snake_str: str) -> str:
    """Convert snake_case to camelCase"""
    if "_" not in snake_str:
        return snake_str

    components = snake_str.split("_")
    return components[0] + "".join(word.capitalize() for word in components[1:])


def camel_to_snake(camel_str: str) -> str:
    """Convert camelCase to snake_case"""
    # Insert underscore before uppercase letters (except first letter)
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", camel_str)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def convert_dict_keys_to_camel(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert all dictionary keys from snake_case to camelCase"""
    if not isinstance(data, dict):
        return data

    result = {}
    for key, value in data.items():
        camel_key = snake_to_camel(key)
        if isinstance(value, dict):
            result[camel_key] = convert_dict_keys_to_camel(value)
        elif isinstance(value, list):
            result[camel_key] = [
                convert_dict_keys_to_camel(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[camel_key] = value

    return result


def convert_dict_keys_to_snake(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert all dictionary keys from camelCase to snake_case"""
    if not isinstance(data, dict):
        return data

    result = {}
    for key, value in data.items():
        snake_key = camel_to_snake(key)
        if isinstance(value, dict):
            result[snake_key] = convert_dict_keys_to_snake(value)
        elif isinstance(value, list):
            result[snake_key] = [
                convert_dict_keys_to_snake(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[snake_key] = value

    return result


class CamelCaseModel(BaseModel):
    """
    Base Pydantic model that automatically converts between snake_case and camelCase.

    - Internal Python code uses snake_case
    - API responses use camelCase
    - API requests accept both formats
    """

    model_config = {
        "alias_generator": to_camel,
        "populate_by_name": True,
    }

    def model_dump(self, by_alias: bool = True, **kwargs) -> Dict[str, Any]:
        """Override model_dump to default to camelCase output"""
        return super().model_dump(by_alias=by_alias, **kwargs)

    def model_dump_json(self, by_alias: bool = True, **kwargs) -> str:
        """Override model_dump_json to default to camelCase output"""
        return super().model_dump_json(by_alias=by_alias, **kwargs)


# Response wrapper that ensures camelCase output
def camel_case_response(data: Any) -> Any:
    """
    Ensure response data is in camelCase format.
    Works with dicts, lists, and Pydantic models.
    """
    if isinstance(data, BaseModel):
        return data.model_dump(by_alias=True)
    elif isinstance(data, dict):
        return convert_dict_keys_to_camel(data)
    elif isinstance(data, list):
        return [camel_case_response(item) for item in data]
    else:
        return data


# Utility decorators for automatic conversion
from functools import wraps
from typing import Callable


def convert_response_to_camel(func: Callable) -> Callable:
    """Decorator to automatically convert response to camelCase"""

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        return camel_case_response(result)

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        return camel_case_response(result)

    # Return appropriate wrapper based on function type
    import asyncio

    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


def generate_temporary_password(length: int = 10) -> str:
    """
    Generate a secure temporary password.

    Args:
        length: Password length (default 10)

    Returns:
        Secure temporary password string
    """
    # Use alphanumeric characters (uppercase, lowercase, digits)
    # Avoid confusing characters like O, 0, I, l, 1
    alphabet = string.ascii_uppercase + string.ascii_lowercase + string.digits
    excluded_chars = {"O", "0", "I", "l", "1"}
    safe_chars = "".join(char for char in alphabet if char not in excluded_chars)

    # Generate secure random password
    password = "".join(secrets.choice(safe_chars) for _ in range(length))

    return password


def validate_college_email(email: str) -> bool:
    """
    Validate if email looks like a college/university email address.

    Args:
        email: Email address to validate

    Returns:
        True if email appears to be from educational institution
    """
    # Common educational domain patterns
    edu_patterns = [
        r"\.edu$",  # .edu domains
        r"\.edu\.",  # .edu. subdomains
        r"\.ac\.",  # Academic domains (.ac.in, .ac.uk)
        r"college\.edu$",  # College domains
        r"university\.edu$",  # University domains
    ]

    email_lower = email.lower()

    # Check against patterns
    for pattern in edu_patterns:
        if re.search(pattern, email_lower):
            return True

    # Additional check for common educational keywords
    edu_keywords = ["college", "university", "institute", "school", "academy"]
    domain = email_lower.split("@")[1] if "@" in email_lower else ""

    for keyword in edu_keywords:
        if keyword in domain:
            return True

    return False
