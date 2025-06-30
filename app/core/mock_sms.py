"""
Mock SMS Service for Development
Uses DEV_OTP from environment for all phone numbers
"""

import logging
from app.config import settings

logger = logging.getLogger(__name__)


class MockSMSService:
    """Mock SMS service for development that uses hardcoded OTP"""
    
    @staticmethod
    def generate_otp() -> str:
        """Generate OTP - returns DEV_OTP for development"""
        return settings.dev_otp
    
    @staticmethod
    async def send_otp_sms(phone_number: str, otp: str) -> dict:
        """
        Mock SMS sending - logs to console instead of actually sending
        
        Args:
            phone_number: Phone number to send SMS to
            otp: OTP code to send
            
        Returns:
            dict: Mock response with success status
        """
        try:
            # Log the mock SMS for development
            logger.info(f"📱 [MOCK SMS] Sending OTP to {phone_number}: {otp}")
            logger.info(f"📱 [MOCK SMS] Message: 'Your verification code is {otp}. Valid for 5 minutes.'")
            
            # Mock successful response
            return {
                "success": True,
                "message_id": f"mock_msg_{phone_number}_{otp}",
                "status": "sent",
                "phone_number": phone_number,
                "otp": otp if settings.debug else None  # Only include OTP in debug mode
            }
            
        except Exception as e:
            logger.error(f"Mock SMS error for {phone_number}: {e}")
            return {
                "success": False,
                "error": str(e),
                "phone_number": phone_number
            }
    
    @staticmethod
    def validate_phone_number(phone_number: str) -> bool:
        """
        Basic phone number validation
        
        Args:
            phone_number: Phone number to validate
            
        Returns:
            bool: True if valid format
        """
        if not phone_number:
            return False
        
        # Remove spaces, dashes, parentheses
        cleaned = phone_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        
        # Basic validation: 10-15 digits, optionally starting with +
        if cleaned.startswith("+"):
            cleaned = cleaned[1:]
        
        # Check if it's all digits and has reasonable length
        return cleaned.isdigit() and 10 <= len(cleaned) <= 15
    
    @staticmethod
    def format_phone_number(phone_number: str) -> str:
        """
        Format phone number to consistent format
        
        Args:
            phone_number: Raw phone number
            
        Returns:
            str: Formatted phone number
        """
        # Remove all non-digit characters except +
        cleaned = ''.join(c for c in phone_number if c.isdigit() or c == '+')
        
        # If it doesn't start with +, assume it's Indian number and add +91
        if not cleaned.startswith('+'):
            # If it's 10 digits, assume it's Indian mobile number
            if len(cleaned) == 10:
                cleaned = '+91' + cleaned
            # If it's already 11+ digits, just add +
            else:
                cleaned = '+' + cleaned
        
        return cleaned


class PhoneOTPManager:
    """Phone-based OTP management using mock SMS service"""
    
    @staticmethod
    def generate_otp() -> str:
        """Generate OTP for phone verification"""
        return MockSMSService.generate_otp()
    
    @staticmethod
    async def send_phone_otp(phone_number: str, purpose: str = "signin") -> dict:
        """
        Send OTP to phone number
        
        Args:
            phone_number: Phone number to send OTP to
            purpose: Purpose of OTP (signin, etc.)
            
        Returns:
            dict: Response with success status and details
        """
        try:
            # Validate phone number
            if not MockSMSService.validate_phone_number(phone_number):
                return {
                    "success": False,
                    "error": "Invalid phone number format"
                }
            
            # Format phone number
            formatted_phone = MockSMSService.format_phone_number(phone_number)
            
            # Generate OTP
            otp = PhoneOTPManager.generate_otp()
            
            # Send SMS (mock)
            sms_result = await MockSMSService.send_otp_sms(formatted_phone, otp)
            
            if sms_result["success"]:
                logger.info(f"Phone OTP sent successfully to {formatted_phone} for {purpose}")
                return {
                    "success": True,
                    "phone_number": formatted_phone,
                    "otp": otp if settings.debug else None,  # Include OTP in debug mode
                    "message": "OTP sent successfully",
                    "purpose": purpose
                }
            else:
                logger.error(f"Failed to send phone OTP to {formatted_phone}: {sms_result.get('error')}")
                return {
                    "success": False,
                    "error": "Failed to send SMS",
                    "details": sms_result
                }
                
        except Exception as e:
            logger.error(f"Phone OTP error for {phone_number}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def verify_phone_otp(phone_number: str, provided_otp: str) -> dict:
        """
        Verify phone OTP
        
        Args:
            phone_number: Phone number
            provided_otp: OTP provided by user
            
        Returns:
            dict: Verification result
        """
        try:
            # Format phone number
            formatted_phone = MockSMSService.format_phone_number(phone_number)
            
            # Check against DEV_OTP
            expected_otp = settings.dev_otp
            
            if provided_otp == expected_otp:
                logger.info(f"Phone OTP verified successfully for {formatted_phone}")
                return {
                    "valid": True,
                    "phone_number": formatted_phone,
                    "message": "OTP verified successfully"
                }
            else:
                logger.warning(f"Invalid phone OTP for {formatted_phone}: expected {expected_otp}, got {provided_otp}")
                return {
                    "valid": False,
                    "phone_number": formatted_phone,
                    "message": "Invalid OTP",
                    "attempts_remaining": 2  # Mock attempt tracking
                }
                
        except Exception as e:
            logger.error(f"Phone OTP verification error for {phone_number}: {e}")
            return {
                "valid": False,
                "error": str(e)
            }