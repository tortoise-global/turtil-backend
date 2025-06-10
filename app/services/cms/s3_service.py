import boto3
from botocore.exceptions import ClientError
from typing import Optional
import uuid
import os
from datetime import datetime

from app.core.config import settings


class S3Service:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket_name = settings.S3_BUCKET_NAME

    def generate_presigned_url(
        self, 
        file_name: str, 
        content_type: Optional[str] = None,
        expiration: int = 3600
    ) -> dict:
        """
        Generate a presigned URL for S3 file upload
        
        Args:
            file_name: Original filename
            content_type: MIME type of the file
            expiration: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            Dict containing presigned URL and file key
        """
        if not self.bucket_name:
            raise ValueError("S3_BUCKET_NAME not configured")
            
        # Generate unique file key
        file_extension = os.path.splitext(file_name)[1]
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        
        # Create folder structure: uploads/YYYY/MM/DD/filename
        now = datetime.now()
        file_key = f"uploads/{now.year}/{now.month:02d}/{now.day:02d}/{unique_filename}"
        
        try:
            # Prepare presigned URL parameters
            params = {
                'Bucket': self.bucket_name,
                'Key': file_key,
            }
            
            # Add content type if provided
            if content_type:
                params['ContentType'] = content_type
            
            # Generate presigned URL for PUT operation
            presigned_url = self.s3_client.generate_presigned_url(
                'put_object',
                Params=params,
                ExpiresIn=expiration
            )
            
            # Generate the public URL for accessing the file after upload
            public_url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{file_key}"
            
            return {
                "presigned_url": presigned_url,
                "file_key": file_key,
                "public_url": public_url,
                "bucket": self.bucket_name,
                "expires_in": expiration
            }
            
        except ClientError as e:
            raise Exception(f"Error generating presigned URL: {str(e)}")

    def delete_file(self, file_key: str) -> bool:
        """
        Delete a file from S3
        
        Args:
            file_key: S3 object key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_key)
            return True
        except ClientError as e:
            print(f"Error deleting file {file_key}: {str(e)}")
            return False

    def check_bucket_exists(self) -> bool:
        """
        Check if the configured S3 bucket exists
        
        Returns:
            True if bucket exists, False otherwise
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return True
        except ClientError:
            return False


# Create singleton instance
s3_service = S3Service()