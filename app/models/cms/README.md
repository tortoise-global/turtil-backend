# CMS Models

This directory contains all database models for the CMS (College Management System) functionality.

## Models

- **User** - User authentication and profile management
- **CollegeDegree** - College degree information
- **CollegePlacement** - Placement records and tracking
- **CollegeStudent** - Student information and management

## Usage

```python
from app.models.cms.models import User, CollegeStudent, CollegeDegree, CollegePlacement
```

## Future Extensions

When adding new services (e.g., LMS, Finance), create separate model directories:
- `app/models/lms/` - Learning Management System models
- `app/models/finance/` - Financial system models
- `app/models/shared/` - Shared models across services