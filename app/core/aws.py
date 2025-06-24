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

    @staticmethod
    async def send_signup_confirmation_email(
        email: str, full_name: str, college_name: str = None
    ) -> Dict[str, Any]:
        """
        Send confirmation email after successful signup
        """
        try:
            ses_client = get_ses_client()
            
            subject = "Welcome to Turtil - Account Created Successfully! 🎉"
            
            # Use college name if provided, otherwise generic message
            college_msg = f"for {college_name}" if college_name else ""
            
            body = f"""
            Welcome {full_name}!
            
            Your Turtil account has been created successfully {college_msg}.
            
            You can now sign in to your account using your email address and the password you set during registration.
            
            If you have any questions or need support, please don't hesitate to contact us.
            
            Welcome aboard!
            The Turtil Team
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
                                    <div style="background-color: #f0f9ff; padding: 30px; border-radius: 8px; border-left: 4px solid #0ea5e9;">
                                        <h2 style="color: #0369a1; margin-bottom: 20px;">🎉 Welcome to Turtil!</h2>
                                        
                                        <p style="font-size: 16px; line-height: 1.5; color: #374151;">
                                            Hi <strong>{full_name}</strong>,
                                        </p>
                                        
                                        <p style="font-size: 16px; line-height: 1.5; color: #374151;">
                                            Congratulations! Your Turtil account has been created successfully {college_msg}.
                                        </p>
                                        
                                        <div style="background-color: white; padding: 20px; border-radius: 6px; margin: 20px 0;">
                                            <h3 style="margin-top: 0; color: #1f2937;">What's Next?</h3>
                                            <ul style="color: #374151; line-height: 1.6;">
                                                <li>You can now sign in using your email address and password</li>
                                                <li>Complete your college setup if you're a Principal</li>
                                                <li>Explore all the features Turtil has to offer</li>
                                            </ul>
                                        </div>
                                        
                                        <div style="background-color: #ecfdf5; padding: 15px; border-radius: 6px; margin: 20px 0; border-left: 4px solid #10b981;">
                                            <h4 style="margin-top: 0; color: #047857;">🔒 Account Security</h4>
                                            <p style="margin: 5px 0; color: #065f46; font-size: 14px;">
                                                Your account is secure. If you notice any suspicious activity, please contact us immediately.
                                            </p>
                                        </div>
                                        
                                        <div style="text-align: center; margin: 30px 0;">
                                            <a href="#" style="background-color: #0ea5e9; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">
                                                Sign In to Your Account
                                            </a>
                                        </div>
                                        
                                        <p style="font-size: 14px; color: #6b7280; text-align: center; margin-top: 30px;">
                                            If you have any questions, feel free to reach out to our support team.
                                        </p>
                                        
                                        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
                                        
                                        <p style="font-size: 12px; color: #9ca3af; text-align: center;">
                                            This is an automated confirmation email from Turtil CMS
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
                f"Signup confirmation email sent successfully to {email}. MessageId: {response['MessageId']}"
            )
            return {
                "success": True,
                "message_id": response["MessageId"],
                "provider": "aws_ses",
            }

        except Exception as e:
            logger.error(f"Failed to send signup confirmation email to {email}: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def send_login_notification_email(
        email: str, full_name: str, device_info: Dict[str, str], ip_address: str, timestamp: str
    ) -> Dict[str, Any]:
        """
        Send notification email after successful login
        """
        try:
            ses_client = get_ses_client()
            
            subject = "New Sign-in to Your Turtil Account"
            
            # Format device info nicely
            device_details = f"{device_info.get('browser', 'Unknown')} on {device_info.get('os', 'Unknown')}"
            device_type = device_info.get('device', 'Unknown')
            
            body = f"""
            Hello {full_name},
            
            We detected a new sign-in to your Turtil account:
            
            Device: {device_details} ({device_type})
            IP Address: {ip_address}
            Time: {timestamp}
            
            If this was you, no action is needed.
            
            If you don't recognize this activity, please:
            1. Change your password immediately
            2. Review your account security settings
            3. Contact our support team if needed
            
            Best regards,
            The Turtil Security Team
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
                                    <div style="background-color: #fefce8; padding: 30px; border-radius: 8px; border-left: 4px solid #eab308;">
                                        <h2 style="color: #a16207; margin-bottom: 20px;">🔐 New Sign-in Detected</h2>
                                        
                                        <p style="font-size: 16px; line-height: 1.5; color: #374151;">
                                            Hello <strong>{full_name}</strong>,
                                        </p>
                                        
                                        <p style="font-size: 16px; line-height: 1.5; color: #374151;">
                                            We detected a new sign-in to your Turtil account:
                                        </p>
                                        
                                        <div style="background-color: white; padding: 20px; border-radius: 6px; margin: 20px 0;">
                                            <h3 style="margin-top: 0; color: #1f2937;">Sign-in Details</h3>
                                            <table style="width: 100%; border-collapse: collapse;">
                                                <tr>
                                                    <td style="padding: 8px 0; color: #6b7280; font-weight: bold;">Device:</td>
                                                    <td style="padding: 8px 0; color: #374151;">{device_details}</td>
                                                </tr>
                                                <tr>
                                                    <td style="padding: 8px 0; color: #6b7280; font-weight: bold;">Type:</td>
                                                    <td style="padding: 8px 0; color: #374151;">{device_type}</td>
                                                </tr>
                                                <tr>
                                                    <td style="padding: 8px 0; color: #6b7280; font-weight: bold;">IP Address:</td>
                                                    <td style="padding: 8px 0; color: #374151;">{ip_address}</td>
                                                </tr>
                                                <tr>
                                                    <td style="padding: 8px 0; color: #6b7280; font-weight: bold;">Time:</td>
                                                    <td style="padding: 8px 0; color: #374151;">{timestamp}</td>
                                                </tr>
                                            </table>
                                        </div>
                                        
                                        <div style="background-color: #dcfce7; padding: 15px; border-radius: 6px; margin: 20px 0; border-left: 4px solid #16a34a;">
                                            <p style="margin: 0; color: #166534; font-size: 14px;">
                                                ✅ <strong>If this was you:</strong> No action needed. You're all set!
                                            </p>
                                        </div>
                                        
                                        <div style="background-color: #fef2f2; padding: 15px; border-radius: 6px; margin: 20px 0; border-left: 4px solid #ef4444;">
                                            <h4 style="margin-top: 0; color: #dc2626;">🚨 If this wasn't you:</h4>
                                            <ol style="margin: 10px 0; color: #dc2626; font-size: 14px;">
                                                <li>Change your password immediately</li>
                                                <li>Review your account security settings</li>
                                                <li>Sign out all other devices</li>
                                                <li>Contact our support team</li>
                                            </ol>
                                        </div>
                                        
                                        <div style="text-align: center; margin: 30px 0;">
                                            <a href="#" style="background-color: #dc2626; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block; margin-right: 10px;">
                                                Secure My Account
                                            </a>
                                            <a href="#" style="background-color: #6b7280; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">
                                                Contact Support
                                            </a>
                                        </div>
                                        
                                        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
                                        
                                        <p style="font-size: 12px; color: #9ca3af; text-align: center;">
                                            This is an automated security notification from Turtil CMS
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
                f"Login notification email sent successfully to {email}. MessageId: {response['MessageId']}"
            )
            return {
                "success": True,
                "message_id": response["MessageId"],
                "provider": "aws_ses",
            }

        except Exception as e:
            logger.error(f"Failed to send login notification email to {email}: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def send_password_reset_confirmation_email(
        email: str, full_name: str, timestamp: str, ip_address: str
    ) -> Dict[str, Any]:
        """
        Send confirmation email after successful password reset
        """
        try:
            ses_client = get_ses_client()
            
            subject = "Password Reset Successful - Turtil Account"
            
            body = f"""
            Hello {full_name},
            
            Your Turtil account password has been successfully reset.
            
            Reset Details:
            - Time: {timestamp}
            - IP Address: {ip_address}
            
            If you made this change, no further action is required.
            
            If you did not reset your password, please contact our support team immediately as your account may be compromised.
            
            For your security:
            - All active sessions have been logged out
            - You'll need to sign in again with your new password
            
            Best regards,
            The Turtil Security Team
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
                                    <div style="background-color: #f0fdf4; padding: 30px; border-radius: 8px; border-left: 4px solid #16a34a;">
                                        <h2 style="color: #166534; margin-bottom: 20px;">🔒 Password Reset Successful</h2>
                                        
                                        <p style="font-size: 16px; line-height: 1.5; color: #374151;">
                                            Hello <strong>{full_name}</strong>,
                                        </p>
                                        
                                        <p style="font-size: 16px; line-height: 1.5; color: #374151;">
                                            Your Turtil account password has been successfully reset.
                                        </p>
                                        
                                        <div style="background-color: white; padding: 20px; border-radius: 6px; margin: 20px 0;">
                                            <h3 style="margin-top: 0; color: #1f2937;">Reset Details</h3>
                                            <table style="width: 100%; border-collapse: collapse;">
                                                <tr>
                                                    <td style="padding: 8px 0; color: #6b7280; font-weight: bold;">Time:</td>
                                                    <td style="padding: 8px 0; color: #374151;">{timestamp}</td>
                                                </tr>
                                                <tr>
                                                    <td style="padding: 8px 0; color: #6b7280; font-weight: bold;">IP Address:</td>
                                                    <td style="padding: 8px 0; color: #374151;">{ip_address}</td>
                                                </tr>
                                            </table>
                                        </div>
                                        
                                        <div style="background-color: #dcfce7; padding: 15px; border-radius: 6px; margin: 20px 0; border-left: 4px solid #16a34a;">
                                            <h4 style="margin-top: 0; color: #166534;">✅ Security Measures Taken</h4>
                                            <ul style="margin: 10px 0; color: #166534; font-size: 14px;">
                                                <li>All active sessions have been logged out</li>
                                                <li>You'll need to sign in again with your new password</li>
                                                <li>Your account security has been enhanced</li>
                                            </ul>
                                        </div>
                                        
                                        <div style="background-color: #fef2f2; padding: 15px; border-radius: 6px; margin: 20px 0; border-left: 4px solid #ef4444;">
                                            <h4 style="margin-top: 0; color: #dc2626;">🚨 Didn't Reset Your Password?</h4>
                                            <p style="margin: 5px 0; color: #dc2626; font-size: 14px;">
                                                If you did not reset your password, your account may be compromised. 
                                                <strong>Contact our support team immediately.</strong>
                                            </p>
                                        </div>
                                        
                                        <div style="text-align: center; margin: 30px 0;">
                                            <a href="#" style="background-color: #16a34a; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block; margin-right: 10px;">
                                                Sign In with New Password
                                            </a>
                                            <a href="#" style="background-color: #ef4444; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">
                                                Report Issue
                                            </a>
                                        </div>
                                        
                                        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
                                        
                                        <p style="font-size: 12px; color: #9ca3af; text-align: center;">
                                            This is an automated security notification from Turtil CMS
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
                f"Password reset confirmation email sent successfully to {email}. MessageId: {response['MessageId']}"
            )
            return {
                "success": True,
                "message_id": response["MessageId"],
                "provider": "aws_ses",
            }

        except Exception as e:
            logger.error(f"Failed to send password reset confirmation email to {email}: {e}")
            return {"success": False, "error": str(e)}


class S3Service:
    """Enhanced S3 service for file uploads with environment-aware configuration"""

    @staticmethod
    def get_environment_bucket_name(bucket_type: str = "storage") -> str:
        """
        Get environment-specific bucket name
        
        Args:
            bucket_type: Type of bucket (storage, logs, terraform-state)
            
        Returns:
            Environment-specific bucket name
        """
        if bucket_type == "logs":
            return settings.logs_s3_bucket_name
        elif bucket_type == "terraform-state":
            return settings.terraform_state_bucket_name
        else:
            return settings.environment_s3_bucket_name

    @staticmethod
    def generate_presigned_url(
        object_name: str, 
        bucket_type: str = "storage",
        expiration: int = 3600,
        conditions: list = None
    ) -> dict:
        """
        Generate a presigned URL for S3 object upload with enhanced security

        Args:
            object_name: Name of the object to upload
            bucket_type: Type of bucket to use (storage, logs, terraform-state)
            expiration: Time in seconds for the presigned URL to remain valid
            conditions: List of conditions for the presigned POST

        Returns:
            Dictionary with presigned URL information
        """
        try:
            s3_client = get_s3_client()
            bucket_name = S3Service.get_environment_bucket_name(bucket_type)

            # Default conditions for security
            if not conditions:
                conditions = [
                    ["content-length-range", 1, 10 * 1024 * 1024],  # Max 10MB
                    {"bucket": bucket_name}
                ]

            # Use presigned POST for better security and control
            response = s3_client.generate_presigned_post(
                Bucket=bucket_name,
                Key=object_name,
                Fields={"Content-Type": S3Service.get_content_type(object_name)},
                Conditions=conditions,
                ExpiresIn=expiration
            )

            logger.info(
                f"Generated presigned URL for {object_name} in {bucket_type} bucket ({bucket_name})"
            )
            
            return {
                "url": response["url"],
                "fields": response["fields"],
                "bucket_name": bucket_name,
                "object_name": object_name,
                "expires_in": expiration,
                "environment": settings.environment
            }

        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise Exception(f"Failed to generate presigned URL: {e}")

    @staticmethod
    def generate_presigned_url_simple(
        bucket_name: str, object_name: str, expiration: int = 3600
    ) -> str:
        """
        Generate a simple presigned URL for S3 object upload (legacy method)

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
    def get_content_type(filename: str) -> str:
        """
        Get content type for a file based on extension
        
        Args:
            filename: Name of the file
            
        Returns:
            MIME content type
        """
        if '.' not in filename:
            return "application/octet-stream"
        
        extension = filename.split('.')[-1].lower()
        
        # Common MIME types
        mime_types = {
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
            "mp4": "video/mp4",
            "mp3": "audio/mpeg",
            "wav": "audio/wav",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        }
        
        return mime_types.get(extension, "application/octet-stream")

    @staticmethod
    def get_object_url(object_name: str, bucket_type: str = "storage") -> str:
        """
        Get the public URL for an S3 object

        Args:
            object_name: Name of the object
            bucket_type: Type of bucket (storage, logs, terraform-state)

        Returns:
            Public URL string
        """
        bucket_name = S3Service.get_environment_bucket_name(bucket_type)
        return f"https://{bucket_name}.s3.{settings.aws_region}.amazonaws.com/{object_name}"

    @staticmethod
    def get_object_url_legacy(bucket_name: str, object_name: str) -> str:
        """
        Get the public URL for an S3 object (legacy method)

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
