from pydantic import BaseModel
from typing import Optional


class PresignedUrlRequest(BaseModel):
    file_name: str


class PresignedUrlResponse(BaseModel):
    statusCode: int
    message: str
    body: Optional[dict] = None