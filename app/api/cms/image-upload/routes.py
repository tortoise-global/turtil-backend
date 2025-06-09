from fastapi import APIRouter, Depends
from app.core.auth import get_current_user
from app.schemas.image_upload import PresignedUrlRequest, PresignedUrlResponse

router = APIRouter()


@router.post("/get-presigned-url", response_model=PresignedUrlResponse)
async def get_presigned_url(
    request: PresignedUrlRequest,
    current_user: dict = Depends(get_current_user)
):
    # TODO: Implement AWS S3 presigned URL generation
    return PresignedUrlResponse(
        statusCode=200,
        message="Presigned URL generated successfully",
        body={
            "presigned_url": f"https://s3.amazonaws.com/bucket/{request.file_name}",
            "file_name": request.file_name
        }
    )