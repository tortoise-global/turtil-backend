import boto3
import logging
from typing import Dict, Any
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
                "ses",
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_ses_region,
            )
        return self._ses_client

    def get_s3_client(self):
        """Get S3 client for file operations"""
        if not self._s3_client:
            self._s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_region,
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
                "region": settings.aws_ses_region,
            }
        except Exception as e:
            health_status["ses"] = {"status": "error", "error": str(e)}

        # Check S3
        try:
            s3_client = self.get_s3_client()
            # Simple call to verify S3 connectivity
            s3_client.list_buckets()
            health_status["s3"] = {"status": "healthy", "region": settings.aws_region}
        except Exception as e:
            health_status["s3"] = {"status": "error", "error": str(e)}

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
                        },
                    },
                },
            )

            logger.info(
                f"Signup OTP email sent successfully via SES. MessageId: {response['MessageId']}"
            )
            return {
                "success": True,
                "message_id": response["MessageId"],
                "provider": "aws_ses",
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
                        },
                    },
                },
            )

            logger.info(
                f"Email sent successfully via SES. MessageId: {response['MessageId']}"
            )
            return {
                "success": True,
                "message_id": response["MessageId"],
                "provider": "aws_ses",
            }

        except Exception as e:
            logger.error(f"Failed to send email via SES: {e}")
            raise Exception(f"Failed to send email: {e}")

    @staticmethod
    async def send_password_reset_otp_email(email: str, otp: str) -> Dict[str, Any]:
        """
        Send password reset OTP email using AWS SES.
        """
        try:
            ses_client = get_ses_client()

            subject = "Reset your Turtil password"
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
                        },
                    },
                },
            )

            logger.info(
                f"Password reset OTP email sent successfully via SES. MessageId: {response['MessageId']}"
            )
            return {
                "success": True,
                "message_id": response["MessageId"],
                "provider": "aws_ses",
            }

        except Exception as e:
            logger.error(f"Failed to send password reset OTP email via SES: {e}")
            raise Exception(f"Failed to send password reset OTP email: {e}")

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
                        },
                    },
                },
            )

            logger.info(
                f"Password reset email sent successfully via SES. MessageId: {response['MessageId']}"
            )
            return {
                "success": True,
                "message_id": response["MessageId"],
                "provider": "aws_ses",
            }

        except Exception as e:
            logger.error(f"Failed to send password reset email via SES: {e}")
            raise Exception(f"Failed to send password reset email: {e}")

    @staticmethod
    async def send_staff_invitation_email(
        email: str, temporary_password: str, inviter_name: str, college_name: str
    ) -> Dict[str, Any]:
        """
        Send staff invitation email with temporary password using AWS SES.
        """
        try:
            ses_client = get_ses_client()

            subject = f"Invitation to join {college_name} on Turtil CMS"
            body = f"""
            You have been invited by {inviter_name} to join {college_name} on Turtil CMS.
            
            Your temporary password is: {temporary_password}
            
            Please sign in using your email and this temporary password. You will be required to set a new password on your first login.
            
            Welcome to Turtil!
            """

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
                                <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                                    <div style="background-color: #f8f9fa; padding: 30px; border-radius: 8px;">
                                        <h2 style="color: #2563eb; margin-bottom: 20px;">You're Invited to Turtil CMS! 🎉</h2>
                                        
                                        <p style="font-size: 16px; line-height: 1.5; color: #374151;">
                                            <strong>{inviter_name}</strong> has invited you to join <strong>{college_name}</strong> on Turtil CMS.
                                        </p>
                                        
                                        <div style="background-color: white; padding: 20px; border-radius: 6px; margin: 20px 0; border-left: 4px solid #2563eb;">
                                            <h3 style="margin-top: 0; color: #1f2937;">Your Login Credentials</h3>
                                            <p style="margin: 5px 0;"><strong>Email:</strong> {email}</p>
                                            <p style="margin: 5px 0;"><strong>Temporary Password:</strong> <code style="background-color: #f3f4f6; padding: 4px 8px; border-radius: 4px; font-weight: bold;">{temporary_password}</code></p>
                                        </div>
                                        
                                        <div style="background-color: #fef3c7; padding: 15px; border-radius: 6px; margin: 20px 0; border-left: 4px solid #f59e0b;">
                                            <h4 style="margin-top: 0; color: #92400e;">⚠️ Important Security Notice</h4>
                                            <ul style="margin: 10px 0; color: #92400e;">
                                                <li>This is a temporary password for your first login only</li>
                                                <li>You will be required to set a new secure password immediately after signing in</li>
                                                <li>Please keep this information secure and do not share it with others</li>
                                            </ul>
                                        </div>
                                        
                                        <div style="text-align: center; margin: 30px 0;">
                                            <a href="#" style="background-color: #2563eb; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">
                                                Sign In to Turtil CMS
                                            </a>
                                        </div>
                                        
                                        <p style="font-size: 14px; color: #6b7280; text-align: center; margin-top: 30px;">
                                            If you did not expect this invitation, please contact {college_name} directly.
                                        </p>
                                        
                                        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
                                        
                                        <p style="font-size: 12px; color: #9ca3af; text-align: center;">
                                            This email was sent by Turtil CMS on behalf of {college_name}
                                        </p>
                                    </div>
                                </body>
                            </html>
                            """
                        },
                    },
                },
            )

            logger.info(
                f"Staff invitation email sent successfully via SES. MessageId: {response['MessageId']}"
            )
            return {
                "success": True,
                "message_id": response["MessageId"],
                "provider": "aws_ses",
            }

        except Exception as e:
            logger.error(f"Failed to send staff invitation email via SES: {e}")
            raise Exception(f"Failed to send staff invitation email: {e}")


class S3Service:
    """S3 service for file uploads"""

    @staticmethod
    def generate_presigned_url(
        bucket_name: str, object_name: str, expiration: int = 3600
    ) -> str:
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
                "put_object",
                Params={"Bucket": bucket_name, "Key": object_name},
                ExpiresIn=expiration,
            )

            logger.info(
                f"Generated presigned URL for {object_name} in bucket {bucket_name}"
            )
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
