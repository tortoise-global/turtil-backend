"""
Notification Model
Store push notification history and delivery status
"""

from sqlalchemy import Column, String, Boolean, DateTime, Integer, JSON, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import UUIDBaseModel
import uuid
from datetime import datetime, timezone


class Notification(UUIDBaseModel):
    """Push notification history model for tracking sent notifications"""

    __tablename__ = "notifications"

    # UUID Primary Key
    notification_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Notification details
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    data_payload = Column(JSON, nullable=True)  # Custom data sent with notification
    
    # Notification settings
    sound = Column(String(50), default="default", nullable=True)
    priority = Column(String(20), default="high", nullable=False)  # "default", "normal", "high"
    ttl = Column(Integer, nullable=True)  # Time to live in seconds
    expiration = Column(Integer, nullable=True)  # Unix timestamp
    
    # College and staff context
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.college_id"), nullable=False, index=True)
    sent_by_staff_id = Column(UUID(as_uuid=True), ForeignKey("staff.staff_id"), nullable=False)
    
    # Target students
    target_student_ids = Column(JSON, nullable=False)  # Array of student UUIDs
    successful_student_ids = Column(JSON, nullable=True)  # Array of students who received notification
    failed_student_ids = Column(JSON, nullable=True)  # Array of students where delivery failed
    
    # Expo Push API response data
    expo_tickets = Column(JSON, nullable=True)  # Push tickets from Expo API
    expo_receipt_ids = Column(JSON, nullable=True)  # Receipt IDs for tracking delivery
    expo_receipts = Column(JSON, nullable=True)  # Delivery receipts from Expo
    
    # Delivery statistics
    total_requested = Column(Integer, default=0, nullable=False)
    total_with_valid_tokens = Column(Integer, default=0, nullable=False)
    total_sent_successfully = Column(Integer, default=0, nullable=False)
    total_failed = Column(Integer, default=0, nullable=False)
    
    # Status tracking
    notification_status = Column(String(20), default="pending", nullable=False, index=True)
    # Status options: "pending", "sent", "failed", "partially_sent"
    
    # Timestamps
    scheduled_at = Column(DateTime(timezone=True), nullable=True)  # For future scheduling
    sent_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Error information
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    
    # Relationships
    college = relationship("College", foreign_keys=[college_id])
    sent_by_staff = relationship("Staff", foreign_keys=[sent_by_staff_id])

    def __repr__(self):
        return f"<Notification(notification_id={self.notification_id}, title={self.title}, college_id={self.college_id})>"

    def mark_as_sent(self, expo_result: dict):
        """Mark notification as sent and store Expo API response"""
        self.notification_status = "sent" if expo_result.get("success") else "failed"
        self.sent_at = datetime.now(timezone.utc)
        
        # Store Expo API response data
        self.expo_tickets = expo_result.get("tickets", [])
        self.expo_receipt_ids = expo_result.get("receipt_ids", [])
        
        # Update statistics
        self.total_requested = expo_result.get("total_requested", 0)
        self.total_with_valid_tokens = expo_result.get("valid_tokens", 0)
        self.total_sent_successfully = expo_result.get("successful_sends", 0)
        self.total_failed = expo_result.get("failed_sends", 0)
        
        # Determine final status
        if self.total_sent_successfully == 0:
            self.notification_status = "failed"
        elif self.total_failed == 0:
            self.notification_status = "sent"
        else:
            self.notification_status = "partially_sent"
        
        # Store error if any
        if not expo_result.get("success") and expo_result.get("error"):
            self.error_message = expo_result["error"]

    def update_delivery_receipts(self, receipt_result: dict):
        """Update notification with delivery receipts from Expo"""
        self.expo_receipts = receipt_result.get("receipts", {})
        self.completed_at = datetime.now(timezone.utc)
        
        # Analyze receipts for final delivery status
        receipts = receipt_result.get("receipts", {})
        successful_deliveries = sum(1 for r in receipts.values() if r.get("status") == "ok")
        failed_deliveries = sum(1 for r in receipts.values() if r.get("status") == "error")
        
        # Update status based on delivery receipts
        if successful_deliveries == 0 and failed_deliveries > 0:
            self.notification_status = "failed"
        elif failed_deliveries == 0 and successful_deliveries > 0:
            self.notification_status = "sent"
        else:
            self.notification_status = "partially_sent"

    def get_delivery_summary(self) -> dict:
        """Get a summary of notification delivery status"""
        return {
            "notification_id": str(self.notification_id),
            "title": self.title,
            "status": self.notification_status,
            "total_requested": self.total_requested,
            "total_with_valid_tokens": self.total_with_valid_tokens,
            "total_sent_successfully": self.total_sent_successfully,
            "total_failed": self.total_failed,
            "sent_at": self.sent_at,
            "completed_at": self.completed_at,
            "error_message": self.error_message,
            "retry_count": self.retry_count
        }

    def can_retry(self) -> bool:
        """Check if notification can be retried"""
        return (self.notification_status in ["failed", "partially_sent"] and 
                self.retry_count < self.max_retries)

    def increment_retry(self):
        """Increment retry counter"""
        self.retry_count += 1

    def to_dict(self) -> dict:
        """Convert to dictionary with camelCase for API responses"""
        base_dict = super().to_dict()
        return {
            "notificationId": base_dict["notification_id"],
            "title": base_dict["title"],
            "body": base_dict["body"],
            "dataPayload": base_dict["data_payload"],
            "sound": base_dict["sound"],
            "priority": base_dict["priority"],
            "ttl": base_dict["ttl"],
            "expiration": base_dict["expiration"],
            "collegeId": base_dict["college_id"],
            "sentByStaffId": base_dict["sent_by_staff_id"],
            "targetStudentIds": base_dict["target_student_ids"],
            "successfulStudentIds": base_dict["successful_student_ids"],
            "failedStudentIds": base_dict["failed_student_ids"],
            "notificationStatus": base_dict["notification_status"],
            "totalRequested": base_dict["total_requested"],
            "totalWithValidTokens": base_dict["total_with_valid_tokens"],
            "totalSentSuccessfully": base_dict["total_sent_successfully"],
            "totalFailed": base_dict["total_failed"],
            "scheduledAt": base_dict["scheduled_at"],
            "sentAt": base_dict["sent_at"],
            "completedAt": base_dict["completed_at"],
            "errorMessage": base_dict["error_message"],
            "retryCount": base_dict["retry_count"],
            "maxRetries": base_dict["max_retries"],
            "createdAt": base_dict["created_at"],
            "updatedAt": base_dict["updated_at"]
        }