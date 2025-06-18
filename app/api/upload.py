from fastapi import APIRouter, Depends
from app.schemas.email import PresignedUrlRequest, PresignedUrlResponse
from app.core.aws import get_s3_client
from app.config import settings
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cms-image-upload", tags=["cms-image-upload"])


@router.post("/generate-presigned-url", response_model=PresignedUrlResponse)
async def generate_presigned_url_endpoint(
    request: PresignedUrlRequest
):
    """
    Generate a pre-signed S3 URL for uploading a file.
    This is your exact existing code integrated into the FastAPI structure.
    """
    try:
        # Initialize the S3 client - exactly as in your code
        s3 = get_s3_client()

        # Bucket name and object key - exactly as in your code
        bucket_name = "my-cms-image-upload"  # Updated bucket name

        files = request.file_name

        print(files)

        object_key = files

        # Allowed file types and their corresponding MIME types - exactly as in your code
        ALLOWED_FILE_TYPES = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "pdf": "application/pdf",
            "doc": "application/msword",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }

        # Determine file extension from the filename - exactly as in your code
        file_extension = files.split(".")[-1].lower()

        # Check if file type is allowed
        if file_extension not in ALLOWED_FILE_TYPES:
            return PresignedUrlResponse(
                status_code=400,
                message=f"File type '{file_extension}' not allowed",
                body=None
            )

        # Generate a pre-signed URL for the S3 object with PutObject permission - exactly as in your code
        url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": bucket_name, 
                "Key": object_key,
                "ContentType": ALLOWED_FILE_TYPES[file_extension]
            },
            ExpiresIn=3600,
            HttpMethod="PUT",
        )

        logger.info(f"Generated presigned URL for {files}")

        return PresignedUrlResponse(
            status_code=200,
            message="Pre-signed URL retrieved successfully",
            body={"presigned_url": url}
        )

    except ClientError as e:
        logger.error("ClientError: %s", e)
        return PresignedUrlResponse(
            status_code=500,
            message="Error generating presigned URL",
            body=None
        )

    except KeyError as e:
        logger.error("KeyError: %s", e)
        return PresignedUrlResponse(
            status_code=400,
            message="Missing required key",
            body=None
        )

    except Exception as e:
        logger.error("Error: %s", e)
        return PresignedUrlResponse(
            status_code=500,
            message="Internal server error",
            body=None
        )


@router.get("/health")
async def upload_health_check():
    """
    Check file upload service health
    """
    try:
        from app.core.aws import check_aws_health
        aws_health = await check_aws_health()
        
        s3_status = aws_health.get("aws", {}).get("s3", {}).get("status", "unknown")
        
        return {
            "status": "healthy" if s3_status == "healthy" else "unhealthy",
            "s3_status": s3_status,
            "bucket_name": "my-cms-image-upload",
            "supported_file_types": ["jpg", "jpeg", "png", "pdf", "doc", "docx"],
            "max_file_size": "10MB",
            "url_expiry": "1 hour"
        }
    except Exception as e:
        logger.error(f"Upload health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/supported-types")
async def get_supported_file_types():
    """
    Get list of supported file types for upload
    """
    return {
        "supported_types": {
            "images": ["jpg", "jpeg", "png"],
            "documents": ["pdf", "doc", "docx"]
        },
        "mime_types": {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg", 
            "png": "image/png",
            "pdf": "application/pdf",
            "doc": "application/msword",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        },
        "max_file_size": "10MB",
        "url_expiry_seconds": 3600
    }