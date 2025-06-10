# CMS Services

This directory contains all business logic services for the CMS (College Management System) functionality.

## Services

- **s3_service.py** - AWS S3 integration for file uploads and management

## Usage

```python
from app.services.cms.s3_service import s3_service
```

## Future Extensions

When adding new services (e.g., LMS, Finance), create separate service directories:
- `app/services/lms/` - Learning Management System services
- `app/services/finance/` - Financial system services  
- `app/services/shared/` - Shared services across systems

## Service Pattern

Each service should:
1. Have a single responsibility
2. Be stateless where possible
3. Include proper error handling
4. Provide a clean interface for the API layer