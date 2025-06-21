from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.staff import Staff
from app.api.cms.auth import get_current_staff
from app.core.aws import get_s3_client
from app.schemas.cms_files import (
    CMSGeneratePresignedUrlRequest,
    CMSGeneratePresignedUrlResponse,
    CMSDeleteFileRequest,
    CMSDeleteFileResponse,
)
from botocore.exceptions import ClientError
import logging
import urllib.parse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cms/files", tags=["CMS File Management"])

# File configuration
BUCKET_NAME = "my-cms-file-upload"

# Common MIME types for reference (not restrictive)
COMMON_MIME_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg", 
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain",
    "csv": "text/csv",
    "json": "application/json",
    "xml": "application/xml",
    "zip": "application/zip",
    "rar": "application/x-rar-compressed",
    "mp4": "video/mp4",
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}

MAX_FILE_SIZE_MB = 10
URL_EXPIRY_SECONDS = 3600


def get_content_type(filename: str) -> str:
    """Get content type for a file, with fallback to binary for unknown types"""
    if '.' not in filename:
        return "application/octet-stream"
    
    extension = filename.split('.')[-1].lower()
    return COMMON_MIME_TYPES.get(extension, "application/octet-stream")


@router.post("/generate-presigned-url", response_model=CMSGeneratePresignedUrlResponse)
async def generate_presigned_url(
    request: CMSGeneratePresignedUrlRequest,
    current_staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a pre-signed S3 URL for uploading files with college-scoped organization.
    
    Files are organized as: bucket/{college_id}/{category}/{filename}
    Categories: images/, documents/, etc.
    """
    try:
        # Get college ID from current staff
        college_id = current_staff.college_id
        if not college_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Staff must be associated with a college"
            )

        # Initialize S3 client
        s3 = get_s3_client()

        # Parse file path and validate
        file_path = request.file_path.strip('/')
        path_parts = file_path.split('/')
        
        if len(path_parts) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File path must include category and filename (e.g., 'images/file.jpg')"
            )

        # Extract filename and get content type
        filename = path_parts[-1]
        if '.' not in filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename must include file extension"
            )

        # Get content type (allows any file type)
        content_type = get_content_type(filename)

        # Create college-scoped S3 key
        s3_key = f"{college_id}/{file_path}"
        
        # Generate pre-signed URL
        presigned_url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": BUCKET_NAME,
                "Key": s3_key,
                "ContentType": content_type,
            },
            ExpiresIn=URL_EXPIRY_SECONDS,
            HttpMethod="PUT",
        )

        logger.info(f"Generated presigned URL for college {college_id}, file: {s3_key}")

        return CMSGeneratePresignedUrlResponse(
            status_code=200,
            message="Pre-signed URL generated successfully",
            presigned_url=presigned_url,
            s3_path=f"s3://{BUCKET_NAME}/{s3_key}"
        )

    except HTTPException:
        raise
    except ClientError as e:
        logger.error(f"S3 ClientError: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate pre-signed URL"
        )
    except Exception as e:
        logger.error(f"Unexpected error generating presigned URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete("/delete", response_model=CMSDeleteFileResponse)
async def delete_file(
    request: CMSDeleteFileRequest,
    current_staff: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a file from S3 with college-scoped security validation.
    
    Only allows deletion of files belonging to the user's college.
    """
    try:
        # Get college ID from current staff
        college_id = current_staff.college_id
        if not college_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Staff must be associated with a college"
            )

        # Initialize S3 client
        s3 = get_s3_client()

        # Parse S3 URL to extract bucket and key
        s3_url = request.s3_url
        
        # Validate URL format
        if not s3_url.startswith('https://') or BUCKET_NAME not in s3_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid S3 URL format"
            )

        # Extract S3 key from URL
        try:
            # Parse URL to get the path after bucket name
            parsed_url = urllib.parse.urlparse(s3_url)
            url_path = parsed_url.path.lstrip('/')
            
            # Remove bucket name prefix if present in path
            if url_path.startswith(f"{BUCKET_NAME}/"):
                s3_key = url_path[len(f"{BUCKET_NAME}/"):]
            else:
                s3_key = url_path
                
        except Exception as e:
            logger.error(f"Error parsing S3 URL: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not parse S3 URL"
            )

        # Validate that the file belongs to the user's college
        if not s3_key.startswith(f"{college_id}/"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete files belonging to your college"
            )

        # Delete the file from S3
        s3.delete_object(Bucket=BUCKET_NAME, Key=s3_key)

        logger.info(f"Deleted file for college {college_id}: {s3_key}")

        return CMSDeleteFileResponse(
            status_code=200,
            message="File deleted successfully",
            deleted_path=s3_key
        )

    except HTTPException:
        raise
    except ClientError as e:
        logger.error(f"S3 ClientError during deletion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file from S3"
        )
    except Exception as e:
        logger.error(f"Unexpected error deleting file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Health and supported types endpoints removed - use /health/detailed for system health
# All file types are supported by default