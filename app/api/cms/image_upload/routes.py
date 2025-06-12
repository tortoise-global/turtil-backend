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
    
    **Request Body:**
    - file_name (string, required): Original filename to upload (e.g., "college_logo.png")
    
    **Path Parameters:** None
    
    **Query Parameters:**
    - content_type (string, optional): MIME type of the file (e.g., "image/png", "image/jpeg")
    - expiration (integer, optional): URL expiration time in seconds (default: 3600, min: 60, max: 604800)
    
    **Headers:**
    - Content-Type: application/json
    - Authorization: Bearer {access_token}
    
    **Example Request:**
    ```json
    {
        "file_name": "college_logo.png"
    }
    ```
    
    **Example Query Parameters:**
    - content_type: "image/png"
    - expiration: 3600
    
    **Example Response:**
    ```json
    {
        "statusCode": 200,
        "message": "Presigned URL generated successfully",
        "body": {
            "presigned_url": "https://turtil-cms-bucket.s3.amazonaws.com/college_logo_1704153600.png?AWSAccessKeyId=...",
            "file_key": "college_logo_1704153600.png",
            "public_url": "https://turtil-cms-bucket.s3.amazonaws.com/college_logo_1704153600.png",
            "bucket": "turtil-cms-bucket",
            "expires_in": 3600,
            "upload_instructions": {
                "method": "PUT",
                "headers": {
                    "Content-Type": "image/png"
                },
                "note": "Use PUT method to upload file to presigned URL"
            }
        }
    }
    ```
    
    **Status Codes:**
    - 200: Presigned URL generated successfully
    - 400: Invalid file name or parameters
    - 401: Unauthorized (invalid token)
    - 500: S3 bucket not configured or not accessible
    
    **Upload Instructions:**
    1. Use the presigned_url with PUT method
    2. Include Content-Type header if specified
    3. Upload the file binary data directly
    4. Access the uploaded file using public_url after successful upload
    
    **Supported File Types:**
    - Images: jpg, jpeg, png, gif, webp
    - Documents: pdf, doc, docx, txt
    - Archives: zip, tar
    - Others: based on content_type parameter
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
    
    **Request Body:** None
    
    **Path Parameters:** None
    
    **Query Parameters:**
    - file_key (string, required): S3 object key to delete (obtained from presigned URL response)
    
    **Headers:**
    - Authorization: Bearer {access_token}
    
    **Example URL:** DELETE /delete-file?file_key=college_logo_1704153600.png
    
    **Example Response:**
    ```json
    {
        "message": "File deleted successfully",
        "file_key": "college_logo_1704153600.png"
    }
    ```
    
    **Status Codes:**
    - 200: File deleted successfully
    - 401: Unauthorized (invalid token)
    - 500: Error deleting file or file not found
    
    **Important Notes:**
    - Once deleted, the file cannot be recovered
    - The file_key should be the same as returned in the presigned URL response
    - Deleting a non-existent file will still return 200 status
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
    
    **Request Body:** None
    
    **Path Parameters:** None
    
    **Query Parameters:** None
    
    **Headers:**
    - Authorization: Bearer {access_token}
    
    **Example URL:** GET /bucket-status
    
    **Success Response:**
    ```json
    {
        "bucket_name": "turtil-cms-bucket",
        "accessible": true,
        "region": "us-east-1"
    }
    ```
    
    **Error Response:**
    ```json
    {
        "bucket_name": "turtil-cms-bucket",
        "accessible": false,
        "error": "NoCredentialsError: Unable to locate credentials"
    }
    ```
    
    **Status Codes:**
    - 200: Bucket status retrieved successfully
    - 401: Unauthorized (invalid token)
    
    **Use Cases:**
    - Verify S3 configuration before file uploads
    - Troubleshoot file upload issues
    - Monitor S3 service availability
    - Check AWS credentials and permissions
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