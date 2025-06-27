"""
Push Notification Service
Expo Push API integration for sending notifications to student mobile apps
"""

import json
import aiohttp
import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.student import Student

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
EXPO_RECEIPT_URL = "https://exp.host/--/api/v2/push/getReceipts"


class PushNotificationService:
    """
    Service for sending push notifications via Expo Push API
    Handles both single and bulk notifications with error management
    """

    @staticmethod
    def validate_expo_token(token: str) -> bool:
        """Validate Expo push token format"""
        if not token:
            return False
        
        # Expo push tokens start with "ExponentPushToken[" and end with "]"
        if not token.startswith("ExponentPushToken[") or not token.endswith("]"):
            return False
        
        # Basic length check (tokens are typically 43-50 characters)
        if len(token) < 25 or len(token) > 200:
            return False
        
        return True

    @staticmethod
    async def resolve_student_tokens(
        student_ids: List[str], 
        college_id: str,
        db: AsyncSession
    ) -> Dict[str, str]:
        """
        Resolve student IDs to their Expo push tokens
        Returns dict mapping student_id -> expo_push_token
        """
        try:
            # Get students with valid expo push tokens from the specified college
            result = await db.execute(
                select(Student.student_id, Student.expo_push_token, Student.full_name)
                .where(Student.student_id.in_(student_ids))
                .where(Student.college_id == college_id)
                .where(Student.expo_push_token.isnot(None))
                .where(Student.expo_push_token != "")
                .where(Student.is_active == True)
            )
            
            student_tokens = {}
            for row in result:
                student_id, expo_token, full_name = row
                if PushNotificationService.validate_expo_token(expo_token):
                    student_tokens[str(student_id)] = expo_token
                else:
                    logger.warning(f"Invalid expo token for student {student_id} ({full_name}): {expo_token}")
            
            logger.info(f"Resolved {len(student_tokens)} valid expo tokens from {len(student_ids)} student IDs")
            return student_tokens
            
        except Exception as e:
            logger.error(f"Failed to resolve student tokens: {e}")
            return {}

    @staticmethod
    async def send_notification(
        expo_tokens: Union[str, List[str]],
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        sound: str = "default",
        priority: str = "high",
        ttl: Optional[int] = None,
        expiration: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send push notification to one or multiple devices
        
        Args:
            expo_tokens: Single token string or list of token strings
            title: Notification title
            body: Notification body text
            data: Optional data payload
            sound: Sound setting ("default" or None)
            priority: Priority ("default", "normal", or "high")
            ttl: Time to live in seconds
            expiration: Unix timestamp expiration
            
        Returns:
            Dict with success status, tickets, and any errors
        """
        try:
            # Prepare notification payload
            if isinstance(expo_tokens, str):
                expo_tokens = [expo_tokens]
            
            # Validate all tokens
            valid_tokens = [token for token in expo_tokens if PushNotificationService.validate_expo_token(token)]
            
            if not valid_tokens:
                return {
                    "success": False,
                    "error": "No valid Expo push tokens provided",
                    "total_requested": len(expo_tokens),
                    "valid_tokens": 0
                }
            
            # Build notification payload
            notification_payload = {
                "to": valid_tokens,
                "title": title,
                "body": body,
                "sound": sound,
                "priority": priority
            }
            
            # Add optional fields
            if data:
                notification_payload["data"] = data
            if ttl is not None:
                notification_payload["ttl"] = ttl
            if expiration is not None:
                notification_payload["expiration"] = expiration
            
            # Send request to Expo Push API
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    EXPO_PUSH_URL,
                    json=notification_payload,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "Accept-Encoding": "gzip, deflate"
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Expo Push API error {response.status}: {error_text}")
                        return {
                            "success": False,
                            "error": f"API error {response.status}: {error_text}",
                            "total_requested": len(expo_tokens),
                            "valid_tokens": len(valid_tokens)
                        }
                    
                    response_data = await response.json()
                    
                    # Process response tickets
                    tickets = response_data.get("data", [])
                    errors = response_data.get("errors", [])
                    
                    successful_tickets = [t for t in tickets if t.get("status") == "ok"]
                    failed_tickets = [t for t in tickets if t.get("status") == "error"]
                    
                    logger.info(f"Push notification sent: {len(successful_tickets)} success, {len(failed_tickets)} failed")
                    
                    return {
                        "success": len(failed_tickets) == 0 and len(errors) == 0,
                        "total_requested": len(expo_tokens),
                        "valid_tokens": len(valid_tokens),
                        "successful_sends": len(successful_tickets),
                        "failed_sends": len(failed_tickets),
                        "tickets": tickets,
                        "errors": errors,
                        "receipt_ids": [t.get("id") for t in successful_tickets if t.get("id")]
                    }
                    
        except aiohttp.ClientError as e:
            logger.error(f"Network error sending push notification: {e}")
            return {
                "success": False,
                "error": f"Network error: {str(e)}",
                "total_requested": len(expo_tokens) if isinstance(expo_tokens, list) else 1,
                "valid_tokens": 0
            }
        except Exception as e:
            logger.error(f"Unexpected error sending push notification: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "total_requested": len(expo_tokens) if isinstance(expo_tokens, list) else 1,
                "valid_tokens": 0
            }

    @staticmethod
    async def send_bulk_notification_to_students(
        student_ids: List[str],
        college_id: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        sound: str = "default",
        priority: str = "high",
        ttl: Optional[int] = None,
        expiration: Optional[int] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Send notification to multiple students by their IDs
        Resolves student IDs to expo tokens and sends bulk notification
        
        Returns:
            Dict with detailed results including which students received notifications
        """
        try:
            if not db:
                return {
                    "success": False,
                    "error": "Database session required",
                    "total_requested": len(student_ids)
                }
            
            # Resolve student IDs to expo tokens
            student_tokens = await PushNotificationService.resolve_student_tokens(
                student_ids, college_id, db
            )
            
            if not student_tokens:
                return {
                    "success": False,
                    "error": "No valid expo tokens found for provided student IDs",
                    "total_requested": len(student_ids),
                    "valid_students": 0
                }
            
            # Send notifications
            expo_tokens = list(student_tokens.values())
            notification_result = await PushNotificationService.send_notification(
                expo_tokens=expo_tokens,
                title=title,
                body=body,
                data=data,
                sound=sound,
                priority=priority,
                ttl=ttl,
                expiration=expiration
            )
            
            # Add student-specific information to the result
            notification_result.update({
                "total_students_requested": len(student_ids),
                "students_with_valid_tokens": len(student_tokens),
                "student_tokens_resolved": student_tokens,
                "sent_at": datetime.now(timezone.utc).isoformat()
            })
            
            return notification_result
            
        except Exception as e:
            logger.error(f"Failed to send bulk notification to students: {e}")
            return {
                "success": False,
                "error": f"Bulk notification failed: {str(e)}",
                "total_students_requested": len(student_ids),
                "students_with_valid_tokens": 0
            }

    @staticmethod
    async def get_push_receipts(receipt_ids: List[str]) -> Dict[str, Any]:
        """
        Get delivery receipts for previously sent notifications
        
        Args:
            receipt_ids: List of receipt IDs from successful push tickets
            
        Returns:
            Dict with receipt information
        """
        try:
            if not receipt_ids:
                return {"success": True, "receipts": {}, "total_requested": 0}
            
            # Request receipts from Expo
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    EXPO_RECEIPT_URL,
                    json={"ids": receipt_ids},
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Expo Receipt API error {response.status}: {error_text}")
                        return {
                            "success": False,
                            "error": f"Receipt API error {response.status}: {error_text}",
                            "total_requested": len(receipt_ids)
                        }
                    
                    response_data = await response.json()
                    receipts = response_data.get("data", {})
                    errors = response_data.get("errors", [])
                    
                    successful_receipts = {k: v for k, v in receipts.items() if v.get("status") == "ok"}
                    failed_receipts = {k: v for k, v in receipts.items() if v.get("status") == "error"}
                    
                    logger.info(f"Retrieved {len(successful_receipts)} successful receipts, {len(failed_receipts)} failed")
                    
                    return {
                        "success": len(errors) == 0,
                        "total_requested": len(receipt_ids),
                        "receipts_found": len(receipts),
                        "successful_receipts": len(successful_receipts),
                        "failed_receipts": len(failed_receipts),
                        "receipts": receipts,
                        "errors": errors
                    }
                    
        except Exception as e:
            logger.error(f"Failed to get push receipts: {e}")
            return {
                "success": False,
                "error": f"Receipt retrieval failed: {str(e)}",
                "total_requested": len(receipt_ids)
            }


# Global service instance
push_notification_service = PushNotificationService()