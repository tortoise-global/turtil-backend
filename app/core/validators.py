import re
from typing import Any
from pydantic import validator


def validate_phone_number(v: str) -> str:
    if v is None:
        return v
    
    phone_pattern = re.compile(r'^\+?1?\d{9,15}$')
    if not phone_pattern.match(v.replace(" ", "").replace("-", "")):
        raise ValueError("Invalid phone number format")
    return v


def validate_student_id(v: str) -> str:
    if not v:
        raise ValueError("Student ID cannot be empty")
    
    if len(v) < 3 or len(v) > 20:
        raise ValueError("Student ID must be between 3 and 20 characters")
    
    if not re.match(r'^[A-Za-z0-9-_]+$', v):
        raise ValueError("Student ID can only contain letters, numbers, hyphens, and underscores")
    
    return v


def validate_institute_code(v: str) -> str:
    if not v:
        raise ValueError("Institute code cannot be empty")
    
    if len(v) < 2 or len(v) > 10:
        raise ValueError("Institute code must be between 2 and 10 characters")
    
    if not re.match(r'^[A-Z0-9]+$', v):
        raise ValueError("Institute code can only contain uppercase letters and numbers")
    
    return v.upper()


def validate_password_strength(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters long")
    
    if not re.search(r'[A-Z]', v):
        raise ValueError("Password must contain at least one uppercase letter")
    
    if not re.search(r'[a-z]', v):
        raise ValueError("Password must contain at least one lowercase letter")
    
    if not re.search(r'\d', v):
        raise ValueError("Password must contain at least one digit")
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
        raise ValueError("Password must contain at least one special character")
    
    return v