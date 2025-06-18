import boto3
import logging
from typing import Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)

class AWSManager:
    """AWS services manager for SES, S3, and other AWS operations"""
    
    def __init__(self):
        self._ses_client = None
        self._s3_client = None
    
    def get_ses_client(self):
        """Get SES client with proper region configuration"""
        if not self._ses_client:
            self._ses_client = boto3.client(
                'ses',
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_ses_region
            )
        return self._ses_client
    
    def get_s3_client(self):
        """Get S3 client for file operations"""
        if not self._s3_client:
            self._s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_region
            )
        return self._s3_client
    
    def health_check(self) -> Dict[str, Any]:
        """Check health of AWS services"""
        health_status = {}
        
        # Check SES
        try:
            ses_client = self.get_ses_client()
            # Simple call to verify SES connectivity
            ses_client.get_send_quota()
            health_status["ses"] = {
                "status": "healthy",
                "region": settings.aws_ses_region
            }
        except Exception as e:
            health_status["ses"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Check S3
        try:
            s3_client = self.get_s3_client()
            # Simple call to verify S3 connectivity
            s3_client.list_buckets()
            health_status["s3"] = {
                "status": "healthy",
                "region": settings.aws_region
            }
        except Exception as e:
            health_status["s3"] = {
                "status": "error",
                "error": str(e)
            }
        
        return health_status

# Global AWS manager instance
aws_manager = AWSManager()

def get_ses_client():
    """Get SES client for email operations"""
    return aws_manager.get_ses_client()

def get_s3_client():
    """Get S3 client for file uploads"""
    return aws_manager.get_s3_client()


class EmailService:
    """Email service using AWS SES"""
    
    @staticmethod
    async def send_signup_otp_email(email: str, otp: str) -> Dict[str, Any]:
        """
        Send signup OTP email using AWS SES.
        """
        try:
            ses_client = get_ses_client()
            
            subject = "Welcome to Turtil - Verify your email"
            body = f"Welcome to Turtil! Your signup verification code is {otp}. Please use this to complete your registration. It is valid for the next 5 minutes."
            
            response = ses_client.send_email(
                Source=settings.aws_ses_from_email,
                Destination={"ToAddresses": [email]},
                Message={
                    "Subject": {"Data": subject},
                    "Body": {
                        "Text": {"Data": body},
                        "Html": {
                            "Data": f"""
                            <html>
                                <body>
                                    <h2>Welcome to Turtil!</h2>
                                    <p>Thanks for signing up! Your verification code is <strong>{otp}</strong></p>
                                    <p>Please use this code to complete your registration.</p>
                                    <p>This code is valid for the next 5 minutes.</p>
                                    <p>If you did not sign up for Turtil, please ignore this email.</p>
                                </body>
                            </html>
                            """
                        }
                    },
                },
            )
            
            logger.info(f"Signup OTP email sent successfully via SES. MessageId: {response['MessageId']}")
            return {
                "success": True,
                "message_id": response['MessageId'],
                "provider": "aws_ses"
            }
            
        except Exception as e:
            logger.error(f"Failed to send signup OTP email via SES: {e}")
            raise Exception(f"Failed to send signup OTP email: {e}")

    @staticmethod
    async def send_otp_email(email: str, otp: str) -> Dict[str, Any]:
        """
        Send OTP email using AWS SES.
        """
        try:
            ses_client = get_ses_client()
            
            subject = "Verify your email address"
            body = f"Your Turtil OTP is {otp}. Please use this to verify your email address. It is valid for the next 5 minutes."
            
            response = ses_client.send_email(
                Source=settings.aws_ses_from_email,
                Destination={"ToAddresses": [email]},
                Message={
                    "Subject": {"Data": subject},
                    "Body": {
                        "Text": {"Data": body},
                        "Html": {
                            "Data": f"""
                            <html>
                                <body>
                                    <h2>Email Verification</h2>
                                    <p>Your Turtil OTP is <strong>{otp}</strong></p>
                                    <p>Please use this to verify your email address.</p>
                                    <p>This OTP is valid for the next 5 minutes.</p>
                                </body>
                            </html>
                            """
                        }
                    },
                },
            )
            
            logger.info(f"Email sent successfully via SES. MessageId: {response['MessageId']}")
            return {
                "success": True,
                "message_id": response['MessageId'],
                "provider": "aws_ses"
            }
            
        except Exception as e:
            logger.error(f"Failed to send email via SES: {e}")
            raise Exception(f"Failed to send email: {e}")
    
    @staticmethod
    async def send_password_reset_email(email: str, otp: str) -> Dict[str, Any]:
        """
        Send password reset email using AWS SES.
        """
        try:
            ses_client = get_ses_client()
            
            subject = "Reset your password"
            body = f"Your Turtil password reset code is {otp}. Please use this to reset your password. It is valid for the next 5 minutes."
            
            response = ses_client.send_email(
                Source=settings.aws_ses_from_email,
                Destination={"ToAddresses": [email]},
                Message={
                    "Subject": {"Data": subject},
                    "Body": {
                        "Text": {"Data": body},
                        "Html": {
                            "Data": f"""
                            <html>
                                <body>
                                    <h2>Password Reset</h2>
                                    <p>Your Turtil password reset code is <strong>{otp}</strong></p>
                                    <p>Please use this to reset your password.</p>
                                    <p>This code is valid for the next 5 minutes.</p>
                                    <p>If you did not request this password reset, please ignore this email.</p>
                                </body>
                            </html>
                            """
                        }
                    },
                },
            )
            
            logger.info(f"Password reset email sent successfully via SES. MessageId: {response['MessageId']}")
            return {
                "success": True,
                "message_id": response['MessageId'],
                "provider": "aws_ses"
            }
            
        except Exception as e:
            logger.error(f"Failed to send password reset email via SES: {e}")
            raise Exception(f"Failed to send password reset email: {e}")


class S3Service:
    """S3 service for file uploads"""
    
    @staticmethod
    def generate_presigned_url(bucket_name: str, object_name: str, expiration: int = 3600) -> str:
        """
        Generate a presigned URL for S3 object upload
        
        Args:
            bucket_name: Name of the S3 bucket
            object_name: Name of the object to upload
            expiration: Time in seconds for the presigned URL to remain valid
            
        Returns:
            Presigned URL string
        """
        try:
            s3_client = get_s3_client()
            
            response = s3_client.generate_presigned_url(
                'put_object',
                Params={'Bucket': bucket_name, 'Key': object_name},
                ExpiresIn=expiration
            )
            
            logger.info(f"Generated presigned URL for {object_name} in bucket {bucket_name}")
            return response
            
        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise Exception(f"Failed to generate presigned URL: {e}")
    
    @staticmethod
    def get_object_url(bucket_name: str, object_name: str) -> str:
        """
        Get the public URL for an S3 object
        
        Args:
            bucket_name: Name of the S3 bucket
            object_name: Name of the object
            
        Returns:
            Public URL string
        """
        return f"https://{bucket_name}.s3.{settings.aws_region}.amazonaws.com/{object_name}"


# Health check function
async def check_aws_health() -> Dict[str, Any]:
    """Check AWS services health"""
    return aws_manager.health_check()