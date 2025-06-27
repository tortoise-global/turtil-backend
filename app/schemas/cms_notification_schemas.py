"""
CMS Notification Management Schemas
Pydantic schemas for push notification send/history endpoints
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.core.utils import CamelCaseModel


# ==================== SEND NOTIFICATION SCHEMAS ====================

class SendNotificationRequest(CamelCaseModel):
    """Request to send push notification to students"""
    student_ids: List[str] = Field(..., min_items=1, max_items=1000, description="List of student UUIDs to notify")
    title: str = Field(..., min_length=1, max_length=200, description="Notification title")
    body: str = Field(..., min_length=1, max_length=1000, description="Notification body text")
    data: Optional[Dict[str, Any]] = Field(None, description="Custom data payload")
    sound: str = Field("default", description="Sound setting")
    priority: str = Field("high", description="Notification priority")
    ttl: Optional[int] = Field(None, ge=60, le=86400, description="Time to live in seconds (60-86400)")
    expiration: Optional[int] = Field(None, description="Unix timestamp expiration")
    
    @validator('priority')
    def validate_priority(cls, v):
        allowed_priorities = ["default", "normal", "high"]
        if v not in allowed_priorities:
            raise ValueError(f"Priority must be one of: {', '.join(allowed_priorities)}")
        return v
    
    @validator('sound')
    def validate_sound(cls, v):
        # Allow "default" or null for silent notifications
        if v and v not in ["default"]:
            # In future, validate custom sound names
            pass
        return v


class NotificationDeliveryStats(BaseModel):
    """Notification delivery statistics"""
    totalRequested: int = Field(..., description="Total students requested for notification")
    studentsWithValidTokens: int = Field(..., description="Students with valid Expo push tokens")
    successfulSends: int = Field(..., description="Successfully sent notifications")
    failedSends: int = Field(..., description="Failed notification sends")


class SendNotificationResponse(BaseModel):
    """Response for send notification request"""
    success: bool = Field(..., description="Overall operation success")
    message: str = Field(..., description="Result message")
    notificationId: str = Field(..., description="Created notification UUID")
    deliveryStats: NotificationDeliveryStats = Field(..., description="Delivery statistics")
    sentAt: datetime = Field(..., description="Notification sent timestamp")
    expoTickets: Optional[List[Dict[str, Any]]] = Field(None, description="Expo push tickets")
    receiptIds: Optional[List[str]] = Field(None, description="Receipt IDs for tracking")


# ==================== NOTIFICATION HISTORY SCHEMAS ====================

class NotificationHistoryFilters(BaseModel):
    """Filters for notification history search"""
    status: Optional[str] = Field(None, description="Filter by status: pending, sent, failed, partially_sent")
    dateFrom: Optional[datetime] = Field(None, description="Filter from date")
    dateTo: Optional[datetime] = Field(None, description="Filter to date")
    sentByStaff: Optional[str] = Field(None, description="Filter by staff who sent notification")


class NotificationHistoryItem(BaseModel):
    """Individual notification in history"""
    notificationId: str = Field(..., description="Notification UUID")
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body")
    status: str = Field(..., description="Delivery status")
    
    # Delivery statistics
    totalRequested: int = Field(..., description="Total students targeted")
    totalWithValidTokens: int = Field(..., description="Students with valid tokens")
    totalSentSuccessfully: int = Field(..., description="Successful deliveries")
    totalFailed: int = Field(..., description="Failed deliveries")
    
    # Timestamps
    sentAt: Optional[datetime] = Field(None, description="When notification was sent")
    completedAt: Optional[datetime] = Field(None, description="When delivery completed")
    createdAt: datetime = Field(..., description="When notification was created")
    
    # Staff who sent
    sentByStaffName: str = Field(..., description="Staff member who sent notification")
    
    # Error information
    errorMessage: Optional[str] = Field(None, description="Error message if failed")
    retryCount: int = Field(0, description="Number of retry attempts")


class NotificationHistoryResponse(BaseModel):
    """Response for notification history listing"""
    notifications: List[NotificationHistoryItem] = Field(..., description="List of notifications")
    total: int = Field(..., description="Total number of notifications")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total number of pages")
    appliedFilters: NotificationHistoryFilters = Field(..., description="Applied filters")


# ==================== NOTIFICATION DETAILS SCHEMAS ====================

class NotificationDetailResponse(BaseModel):
    """Detailed information about a specific notification"""
    notificationId: str = Field(..., description="Notification UUID")
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body")
    dataPayload: Optional[Dict[str, Any]] = Field(None, description="Custom data payload")
    
    # Settings
    sound: Optional[str] = Field(None, description="Sound setting")
    priority: str = Field(..., description="Notification priority")
    ttl: Optional[int] = Field(None, description="Time to live in seconds")
    expiration: Optional[int] = Field(None, description="Unix timestamp expiration")
    
    # Status and statistics
    status: str = Field(..., description="Delivery status")
    totalRequested: int = Field(..., description="Total students targeted")
    totalWithValidTokens: int = Field(..., description="Students with valid tokens")
    totalSentSuccessfully: int = Field(..., description="Successful deliveries")
    totalFailed: int = Field(..., description="Failed deliveries")
    
    # Target information
    targetStudentIds: List[str] = Field(..., description="List of targeted student UUIDs")
    successfulStudentIds: Optional[List[str]] = Field(None, description="Students who received notification")
    failedStudentIds: Optional[List[str]] = Field(None, description="Students where delivery failed")
    
    # Timestamps
    scheduledAt: Optional[datetime] = Field(None, description="Scheduled send time")
    sentAt: Optional[datetime] = Field(None, description="Actually sent time")
    completedAt: Optional[datetime] = Field(None, description="Delivery completion time")
    createdAt: datetime = Field(..., description="Creation timestamp")
    updatedAt: datetime = Field(..., description="Last update timestamp")
    
    # Staff context
    sentByStaffName: str = Field(..., description="Staff member who sent notification")
    collegeName: str = Field(..., description="College name")
    
    # Technical details
    expoTickets: Optional[List[Dict[str, Any]]] = Field(None, description="Expo push tickets")
    expoReceiptIds: Optional[List[str]] = Field(None, description="Expo receipt IDs")
    expoReceipts: Optional[Dict[str, Any]] = Field(None, description="Expo delivery receipts")
    errorMessage: Optional[str] = Field(None, description="Error message if failed")
    retryCount: int = Field(0, description="Number of retry attempts")
    maxRetries: int = Field(3, description="Maximum retry attempts")


# ==================== RETRY AND BULK OPERATIONS ====================

class RetryNotificationRequest(BaseModel):
    """Request to retry a failed notification"""
    notificationId: str = Field(..., description="Notification UUID to retry")


class RetryNotificationResponse(BaseModel):
    """Response for notification retry"""
    success: bool = Field(..., description="Retry operation success")
    message: str = Field(..., description="Result message")
    notificationId: str = Field(..., description="Notification UUID")
    newDeliveryStats: NotificationDeliveryStats = Field(..., description="Updated delivery statistics")
    retriedAt: datetime = Field(..., description="Retry timestamp")


class BulkNotificationAction(BaseModel):
    """Bulk action on multiple notifications"""
    notificationIds: List[str] = Field(..., min_items=1, max_items=100, description="List of notification UUIDs")
    action: str = Field(..., description="Action to perform: retry, delete")
    
    @validator('action')
    def validate_action(cls, v):
        allowed_actions = ["retry", "delete"]
        if v not in allowed_actions:
            raise ValueError(f"Action must be one of: {', '.join(allowed_actions)}")
        return v


class BulkNotificationResponse(BaseModel):
    """Response for bulk notification operations"""
    success: bool = Field(..., description="Overall operation success")
    message: str = Field(..., description="Result message")
    totalRequested: int = Field(..., description="Total notifications requested for action")
    successfulActions: int = Field(..., description="Successful actions performed")
    failedActions: int = Field(..., description="Failed actions")
    actionResults: List[Dict[str, Any]] = Field(..., description="Detailed results per notification")
    processedAt: datetime = Field(..., description="Processing timestamp")


# ==================== STATISTICS SCHEMAS ====================

class NotificationStatistics(BaseModel):
    """Notification statistics for dashboard"""
    totalNotifications: int = Field(..., description="Total notifications sent")
    successfulNotifications: int = Field(..., description="Successfully delivered notifications")
    failedNotifications: int = Field(..., description="Failed notifications")
    partiallySuccessfulNotifications: int = Field(..., description="Partially delivered notifications")
    
    # Time-based statistics
    notificationsToday: int = Field(..., description="Notifications sent today")
    notificationsThisWeek: int = Field(..., description="Notifications sent this week")
    notificationsThisMonth: int = Field(..., description="Notifications sent this month")
    
    # Student engagement
    studentsReached: int = Field(..., description="Unique students who received notifications")
    averageDeliveryRate: float = Field(..., description="Average delivery success rate (0-100)")
    
    # Recent activity
    recentNotifications: List[NotificationHistoryItem] = Field(..., description="Recent notifications (last 10)")


class NotificationStatisticsResponse(BaseModel):
    """Response for notification statistics"""
    success: bool = True
    message: str = "Notification statistics retrieved successfully"
    collegeName: str = Field(..., description="College name")
    statistics: NotificationStatistics = Field(..., description="Detailed statistics")
    generatedAt: datetime = Field(..., description="When statistics were generated")


# ==================== ERROR SCHEMAS ====================

class NotificationError(BaseModel):
    """Notification operation error response"""
    statusCode: int = Field(..., description="HTTP status code")
    message: str = Field(..., description="Error message")
    success: bool = False
    timestamp: datetime = Field(..., description="Error timestamp")
    notificationId: Optional[str] = Field(None, description="Notification ID if applicable")
    operation: Optional[str] = Field(None, description="Operation that failed")


# ==================== EXPO-SPECIFIC SCHEMAS ====================

class ExpoReceiptStatus(BaseModel):
    """Expo delivery receipt status"""
    receiptId: str = Field(..., description="Receipt ID")
    status: str = Field(..., description="Delivery status: ok, error")
    message: Optional[str] = Field(None, description="Error message if failed")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")


class GetReceiptsRequest(BaseModel):
    """Request to get Expo push receipts"""
    notificationId: str = Field(..., description="Notification UUID")


class GetReceiptsResponse(BaseModel):
    """Response for Expo push receipts"""
    success: bool = Field(..., description="Operation success")
    message: str = Field(..., description="Result message")
    notificationId: str = Field(..., description="Notification UUID")
    receipts: List[ExpoReceiptStatus] = Field(..., description="Delivery receipts")
    totalReceipts: int = Field(..., description="Total receipts checked")
    successfulDeliveries: int = Field(..., description="Successful deliveries")
    failedDeliveries: int = Field(..., description="Failed deliveries")
    checkedAt: datetime = Field(..., description="When receipts were checked")