from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from app.core.auth import get_current_user
from app.schemas.cms.image_upload import PresignedUrlRequest, PresignedUrlResponse
from app.services.cms.s3_service import s3_service

router = APIRouter()


@router.post("/get-presigned-url", response_model=PresignedUrlResponse)
async def get_presigned_url(
    request: PresignedUrlRequest,
    content_type: Optional[str] = Query(None, description="MIME type of the file"),
    expiration: int = Query(3600, description="URL expiration time in seconds", ge=60, le=604800),
    current_user: dict = Depends(get_current_user)
):
    """
    Generate a presigned URL for S3 file upload
    
    - **file_name**: Original filename to upload
    - **content_type**: MIME type of the file (optional)
    - **expiration**: URL expiration time in seconds (60 seconds to 7 days)
    """
    try:
        # Check if S3 bucket exists
        if not s3_service.check_bucket_exists():
            raise HTTPException(
                status_code=500, 
                detail="S3 bucket not configured or not accessible"
            )
        
        # Generate presigned URL
        result = s3_service.generate_presigned_url(
            file_name=request.file_name,
            content_type=content_type,
            expiration=expiration
        )
        
        return PresignedUrlResponse(
            statusCode=200,
            message="Presigned URL generated successfully",
            body={
                "presigned_url": result["presigned_url"],
                "file_key": result["file_key"],
                "public_url": result["public_url"],
                "bucket": result["bucket"],
                "expires_in": result["expires_in"],
                "upload_instructions": {
                    "method": "PUT",
                    "headers": {"Content-Type": content_type} if content_type else {},
                    "note": "Use PUT method to upload file to presigned URL"
                }
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate presigned URL: {str(e)}")


@router.delete("/delete-file")
async def delete_file(
    file_key: str = Query(..., description="S3 file key to delete"),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a file from S3
    
    - **file_key**: S3 object key to delete
    """
    try:
        success = s3_service.delete_file(file_key)
        if success:
            return {"message": "File deleted successfully", "file_key": file_key}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")


@router.get("/bucket-status")
async def check_bucket_status(current_user: dict = Depends(get_current_user)):
    """
    Check S3 bucket configuration and accessibility
    """
    try:
        bucket_exists = s3_service.check_bucket_exists()
        return {
            "bucket_name": s3_service.bucket_name,
            "accessible": bucket_exists,
            "region": s3_service.s3_client._client_config.region_name
        }
    except Exception as e:
        return {
            "bucket_name": s3_service.bucket_name,
            "accessible": False,
            "error": str(e)
        }