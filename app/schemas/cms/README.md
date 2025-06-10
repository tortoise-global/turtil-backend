# CMS Schemas

This directory contains all Pydantic schemas for the CMS (College Management System) functionality.

## Schema Files

- **auth.py** - Authentication and user management schemas
- **college_degree.py** - College degree management schemas
- **college_placements.py** - Placement tracking schemas
- **college_students.py** - Student management schemas
- **image_upload.py** - File upload schemas

## Usage

```python
from app.schemas.cms.auth import UserCreate, UserResponse
from app.schemas.cms.college_students import CollegeStudentCreate
```

## Future Extensions

When adding new services (e.g., LMS, Finance), create separate schema directories:
- `app/schemas/lms/` - Learning Management System schemas
- `app/schemas/finance/` - Financial system schemas
- `app/schemas/shared/` - Shared schemas across systems

## Schema Pattern

Each schema should:
1. Use clear, descriptive names
2. Include proper validation
3. Have separate Create, Update, and Response models
4. Include docstrings for complex fields