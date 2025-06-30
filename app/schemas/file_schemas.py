from pydantic import Field, field_validator
from typing import Optional
from app.core.utils import CamelCaseModel


class CMSGeneratePresignedUrlRequest(CamelCaseModel):
    """Request schema for generating college-scoped presigned URL"""

    file_path: str = Field(
        ..., 
        description="File path within college folder (e.g., 'images/profile.jpg', 'documents/report.pdf')"
    )

    @field_validator('file_path')
    @classmethod
    def validate_file_path(cls, v):
        if not v or v.strip() == "":
            raise ValueError("File path cannot be empty")
        
        # Remove leading slash if present
        v = v.lstrip('/')
        
        # Validate path format
        if not ('/' in v and len(v.split('/')) >= 2):
            raise ValueError("File path must include category and filename (e.g., 'images/file.jpg')")
        
        # Validate filename has extension (but allow any extension)
        filename = v.split('/')[-1]
        if '.' not in filename:
            raise ValueError("Filename must include file extension")
        
        return v


class CMSGeneratePresignedUrlResponse(CamelCaseModel):
    """Response schema for presigned URL generation"""

    status_code: int = Field(..., alias="statusCode", description="HTTP status code")
    message: str = Field(..., description="Response message")
    presigned_url: Optional[str] = Field(None, description="Pre-signed URL for upload")
    s3_path: Optional[str] = Field(None, description="Full S3 path where file will be stored")


class CMSDeleteFileRequest(CamelCaseModel):
    """Request schema for deleting college-scoped files"""

    s3_url: str = Field(
        ..., 
        description="Full S3 URL of the file to delete (must belong to user's college)"
    )

    @field_validator('s3_url')
    @classmethod
    def validate_s3_url(cls, v):
        if not v or not v.startswith('https://'):
            raise ValueError("Invalid S3 URL format")
        
        if 'turtil-backend-dev' not in v:
            raise ValueError("URL must be from the CMS file upload bucket")
        
        return v


class CMSDeleteFileResponse(CamelCaseModel):
    """Response schema for file deletion"""

    status_code: int = Field(..., alias="statusCode", description="HTTP status code")
    message: str = Field(..., description="Response message")
    deleted_path: Optional[str] = Field(None, description="Path of deleted file")


# Health and supported types schemas removed - use /health/detailed for system health
# All file types are supported by default