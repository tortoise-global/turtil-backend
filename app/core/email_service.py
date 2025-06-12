import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Email service using Gmail SMTP for sending OTP and other emails"""

    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = settings.GMAIL_EMAIL
        self.sender_password = settings.GMAIL_APP_PASSWORD

    def _validate_credentials(self):
        """Validate that email credentials are configured"""
        if not self.sender_email or not self.sender_password:
            raise ValueError(
                "Gmail credentials not configured. Please set GMAIL_EMAIL and GMAIL_APP_PASSWORD"
            )

    def send_email(
        self, to_email: str, subject: str, body: str, html_body: Optional[str] = None
    ) -> bool:
        """
        Send an email using Gmail SMTP

        Args:
            to_email (str): Recipient email
            subject (str): Email subject
            body (str): Plain text email body
            html_body (str, optional): HTML email body

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            self._validate_credentials()

            # Create message
            msg = MIMEMultipart("alternative")
            msg["From"] = self.sender_email
            msg["To"] = to_email
            msg["Subject"] = subject

            # Add plain text body
            msg.attach(MIMEText(body, "plain"))

            # Add HTML body if provided
            if html_body:
                msg.attach(MIMEText(html_body, "html"))

            # Connect to Gmail SMTP server
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()  # Enable TLS encryption
            server.login(self.sender_email, self.sender_password)

            # Send email
            text = msg.as_string()
            server.sendmail(self.sender_email, to_email, text)
            server.quit()

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {str(e)}")
            return False

    def send_otp_email(
        self, to_email: str, otp: str, college_name: Optional[str] = None
    ) -> bool:
        """
        Send OTP verification email with professional formatting

        Args:
            to_email (str): Recipient email
            otp (str): OTP code to send
            college_name (str, optional): Name of the college for personalization

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        college_display = college_name or "Turtil CMS"

        subject = f"Your OTP for {college_display} - Verification Code"

        # Plain text version
        plain_body = f"""
Hello,

Your One-Time Password (OTP) for {college_display} is: {otp}

This OTP is valid for {settings.OTP_EXPIRY_MINUTES} minutes.

Please do not share this code with anyone.

If you did not request this OTP, please ignore this email.

Best regards,
{college_display} Team
        """.strip()

        # HTML version for better formatting
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #007bff;">
                    <h2 style="color: #333; margin-top: 0;">Email Verification</h2>
                    <p style="color: #666; font-size: 16px;">Hello,</p>
                    
                    <p style="color: #666; font-size: 16px;">
                        Your One-Time Password (OTP) for <strong>{college_display}</strong> is:
                    </p>
                    
                    <div style="background-color: #007bff; color: white; padding: 15px; text-align: center; font-size: 24px; font-weight: bold; border-radius: 4px; margin: 20px 0; letter-spacing: 2px;">
                        {otp}
                    </div>
                    
                    <p style="color: #666; font-size: 14px;">
                        <strong>Important:</strong>
                    </p>
                    <ul style="color: #666; font-size: 14px;">
                        <li>This OTP is valid for {settings.OTP_EXPIRY_MINUTES} minutes</li>
                        <li>Please do not share this code with anyone</li>
                        <li>If you did not request this OTP, please ignore this email</li>
                    </ul>
                    
                    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                    
                    <p style="color: #999; font-size: 12px; text-align: center;">
                        Best regards,<br>
                        <strong>{college_display} Team</strong>
                    </p>
                </div>
            </body>
        </html>
        """

        return self.send_email(to_email, subject, plain_body, html_body)


# Global email service instance
email_service = EmailService()
