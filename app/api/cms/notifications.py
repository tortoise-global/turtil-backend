"""
CMS Notification Management API
Send and manage push notifications to students
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.security import HTTPBearer
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate as sqlalchemy_paginate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload, joinedload
from typing import Optional, List
import uuid
import logging
from datetime import datetime, timezone

from app.database import get_db
from app.models.staff import Staff
from app.models.student import Student
from app.models.college import College
from app.models.notification import Notification
from app.core.push_notifications import push_notification_service
from app.schemas.cms_notification_schemas import (
    SendNotificationRequest, SendNotificationResponse, NotificationDeliveryStats,
    NotificationHistoryResponse, NotificationHistoryItem, NotificationHistoryFilters,
    NotificationDetailResponse, RetryNotificationRequest, RetryNotificationResponse,
    NotificationStatisticsResponse, NotificationStatistics, GetReceiptsRequest, GetReceiptsResponse
)
from .deps import get_current_staff

router = APIRouter(prefix="/cms/notifications", tags=["CMS Notification Management"])
security = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


@router.post("/send", response_model=SendNotificationResponse, dependencies=[Depends(security)])
async def send_notification(
    request: SendNotificationRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Send push notification to multiple students
    """
    try:
        # Verify staff has permission (principal and college_admin can send notifications)
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can send notifications"
            )
        
        # Validate student IDs belong to the staff's college
        student_ids = request.student_ids
        college_id = str(current_staff.college_id)
        
        # Create notification record in database
        notification = Notification(
            title=request.title,
            body=request.body,
            data_payload=request.data,
            sound=request.sound,
            priority=request.priority,
            ttl=request.ttl,
            expiration=request.expiration,
            college_id=current_staff.college_id,
            sent_by_staff_id=current_staff.staff_id,
            target_student_ids=student_ids,
            notification_status="pending",
            total_requested=len(student_ids)
        )
        
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        
        # Send notification via push service
        push_result = await push_notification_service.send_bulk_notification_to_students(
            student_ids=student_ids,
            college_id=college_id,
            title=request.title,
            body=request.body,
            data=request.data,
            sound=request.sound,
            priority=request.priority,
            ttl=request.ttl,
            expiration=request.expiration,
            db=db
        )
        
        # Update notification with send results
        notification.mark_as_sent(push_result)
        await db.commit()
        
        logger.info(f"Notification sent by {current_staff.full_name} to {len(student_ids)} students: {push_result.get('successful_sends', 0)} successful")
        
        # Build response
        delivery_stats = NotificationDeliveryStats(
            totalRequested=push_result.get("total_students_requested", len(student_ids)),
            studentsWithValidTokens=push_result.get("students_with_valid_tokens", 0),
            successfulSends=push_result.get("successful_sends", 0),
            failedSends=push_result.get("failed_sends", 0)
        )
        
        return SendNotificationResponse(
            success=push_result.get("success", False),
            message=f"Notification sent to {push_result.get('successful_sends', 0)} out of {len(student_ids)} students",
            notificationId=str(notification.notification_id),
            deliveryStats=delivery_stats,
            sentAt=notification.sent_at or datetime.now(timezone.utc),
            expoTickets=push_result.get("tickets"),
            receiptIds=push_result.get("receipt_ids")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Send notification", {"staff_id": str(current_staff.staff_id), "student_count": len(request.studentIds), "title": request.title}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/history", response_model=Page[NotificationHistoryItem], dependencies=[Depends(security)])
async def get_notification_history(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    date_from: Optional[str] = Query(None, description="Filter from date (ISO format)"),
    date_to: Optional[str] = Query(None, description="Filter to date (ISO format)"),
    sent_by_staff: Optional[str] = Query(None, description="Filter by staff name"),
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """
    Get notification history for the college with filtering and pagination
    """
    try:
        # Build base query for notifications in staff's college
        query = (
            select(Notification, Staff.full_name.label("sent_by_staff_name"))
            .join(Staff, Notification.sent_by_staff_id == Staff.staff_id)
            .where(Notification.college_id == current_staff.college_id)
        )
        
        # Apply filters
        if status_filter:
            query = query.where(Notification.notification_status == status_filter)
        
        if date_from:
            try:
                from_date = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                query = query.where(Notification.created_at >= from_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_from format")
        
        if date_to:
            try:
                to_date = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                query = query.where(Notification.created_at <= to_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_to format")
        
        if sent_by_staff:
            query = query.where(Staff.full_name.ilike(f"%{sent_by_staff}%"))
        
        # Order by creation date (newest first)
        query = query.order_by(desc(Notification.created_at))
        
        # Execute paginated query
        paginated_result = await sqlalchemy_paginate(db, query)
        
        # Build response items
        history_items = []
        for row in paginated_result.items:
            notification = row[0]
            sent_by_staff_name = row[1]
            
            history_items.append(NotificationHistoryItem(
                notificationId=str(notification.notification_id),
                title=notification.title,
                body=notification.body,
                status=notification.notification_status,
                totalRequested=notification.total_requested,
                totalWithValidTokens=notification.total_with_valid_tokens,
                totalSentSuccessfully=notification.total_sent_successfully,
                totalFailed=notification.total_failed,
                sentAt=notification.sent_at,
                completedAt=notification.completed_at,
                createdAt=notification.created_at,
                sentByStaffName=sent_by_staff_name,
                errorMessage=notification.error_message,
                retryCount=notification.retry_count
            ))
        
        # Return standard Page response
        return Page(
            items=history_items,
            total=paginated_result.total,
            page=paginated_result.page,
            size=paginated_result.size,
            pages=paginated_result.pages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Get notification history", {"staff_id": str(current_staff.staff_id), "status_filter": status_filter, "date_from": date_from}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/{notification_id}", response_model=NotificationDetailResponse, dependencies=[Depends(security)])
async def get_notification_details(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Get detailed information about a specific notification"""
    try:
        # Get notification with related data
        result = await db.execute(
            select(Notification, Staff.full_name.label("sent_by_staff_name"), College.name.label("college_name"))
            .join(Staff, Notification.sent_by_staff_id == Staff.staff_id)
            .join(College, Notification.college_id == College.college_id)
            .where(Notification.notification_id == notification_id)
            .where(Notification.college_id == current_staff.college_id)
        )
        
        row = result.first()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        notification, sent_by_staff_name, college_name = row
        
        return NotificationDetailResponse(
            notificationId=str(notification.notification_id),
            title=notification.title,
            body=notification.body,
            dataPayload=notification.data_payload,
            sound=notification.sound,
            priority=notification.priority,
            ttl=notification.ttl,
            expiration=notification.expiration,
            status=notification.notification_status,
            totalRequested=notification.total_requested,
            totalWithValidTokens=notification.total_with_valid_tokens,
            totalSentSuccessfully=notification.total_sent_successfully,
            totalFailed=notification.total_failed,
            targetStudentIds=notification.target_student_ids or [],
            successfulStudentIds=notification.successful_student_ids or [],
            failedStudentIds=notification.failed_student_ids or [],
            scheduledAt=notification.scheduled_at,
            sentAt=notification.sent_at,
            completedAt=notification.completed_at,
            createdAt=notification.created_at,
            updatedAt=notification.updated_at,
            sentByStaffName=sent_by_staff_name,
            collegeName=college_name,
            expoTickets=notification.expo_tickets,
            expoReceiptIds=notification.expo_receipt_ids,
            expoReceipts=notification.expo_receipts,
            errorMessage=notification.error_message,
            retryCount=notification.retry_count,
            maxRetries=notification.max_retries
        )
        
    except HTTPException:
        raise
    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Get notification details", {"staff_id": str(current_staff.staff_id), "notification_id": notification_id}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("/{notification_id}/retry", response_model=RetryNotificationResponse, dependencies=[Depends(security)])
async def retry_notification(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Retry a failed or partially failed notification"""
    try:
        # Verify staff has permission
        if current_staff.cms_role not in ["principal", "college_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Principal and College Admin can retry notifications"
            )
        
        # Get notification
        result = await db.execute(
            select(Notification)
            .where(Notification.notification_id == notification_id)
            .where(Notification.college_id == current_staff.college_id)
        )
        notification = result.scalar_one_or_none()
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        # Check if notification can be retried
        if not notification.can_retry():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Notification cannot be retried. Status: {notification.notification_status}, Retries: {notification.retry_count}/{notification.max_retries}"
            )
        
        # Increment retry counter
        notification.increment_retry()
        
        # Retry sending the notification
        push_result = await push_notification_service.send_bulk_notification_to_students(
            student_ids=notification.target_student_ids,
            college_id=str(current_staff.college_id),
            title=notification.title,
            body=notification.body,
            data=notification.data_payload,
            sound=notification.sound,
            priority=notification.priority,
            ttl=notification.ttl,
            expiration=notification.expiration,
            db=db
        )
        
        # Update notification with retry results
        notification.mark_as_sent(push_result)
        await db.commit()
        
        logger.info(f"Notification {notification_id} retried by {current_staff.full_name}: {push_result.get('successful_sends', 0)} successful")
        
        delivery_stats = NotificationDeliveryStats(
            totalRequested=push_result.get("total_students_requested", len(notification.target_student_ids)),
            studentsWithValidTokens=push_result.get("students_with_valid_tokens", 0),
            successfulSends=push_result.get("successful_sends", 0),
            failedSends=push_result.get("failed_sends", 0)
        )
        
        return RetryNotificationResponse(
            success=push_result.get("success", False),
            message=f"Notification retry completed: {push_result.get('successful_sends', 0)} successful sends",
            notificationId=str(notification.notification_id),
            newDeliveryStats=delivery_stats,
            retriedAt=datetime.now(timezone.utc)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Retry notification", {"staff_id": str(current_staff.staff_id), "notification_id": notification_id}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/stats/overview", response_model=NotificationStatisticsResponse, dependencies=[Depends(security)])
async def get_notification_statistics(
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
):
    """Get notification statistics for the college"""
    try:
        from datetime import timedelta
        
        college_id = current_staff.college_id
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)
        month_start = today_start - timedelta(days=30)
        
        # Get college info
        college_result = await db.execute(
            select(College.name).where(College.college_id == college_id)
        )
        college_name = college_result.scalar() or "Unknown College"
        
        # Total notifications
        total_result = await db.execute(
            select(func.count(Notification.notification_id))
            .where(Notification.college_id == college_id)
        )
        total_notifications = total_result.scalar() or 0
        
        # Status-based counts
        status_results = await db.execute(
            select(
                Notification.notification_status,
                func.count(Notification.notification_id)
            )
            .where(Notification.college_id == college_id)
            .group_by(Notification.notification_status)
        )
        
        status_counts = {}
        for status, count in status_results:
            status_counts[status] = count
        
        # Time-based counts
        today_result = await db.execute(
            select(func.count(Notification.notification_id))
            .where(Notification.college_id == college_id)
            .where(Notification.created_at >= today_start)
        )
        notifications_today = today_result.scalar() or 0
        
        week_result = await db.execute(
            select(func.count(Notification.notification_id))
            .where(Notification.college_id == college_id)
            .where(Notification.created_at >= week_start)
        )
        notifications_this_week = week_result.scalar() or 0
        
        month_result = await db.execute(
            select(func.count(Notification.notification_id))
            .where(Notification.college_id == college_id)
            .where(Notification.created_at >= month_start)
        )
        notifications_this_month = month_result.scalar() or 0
        
        # Calculate delivery rate
        total_sent = status_counts.get("sent", 0)
        total_partial = status_counts.get("partially_sent", 0)
        average_delivery_rate = (total_sent + (total_partial * 0.5)) / max(total_notifications, 1) * 100
        
        # Get recent notifications
        recent_result = await db.execute(
            select(Notification, Staff.full_name.label("sent_by_staff_name"))
            .join(Staff, Notification.sent_by_staff_id == Staff.staff_id)
            .where(Notification.college_id == college_id)
            .order_by(desc(Notification.created_at))
            .limit(10)
        )
        
        recent_notifications = []
        for row in recent_result:
            notification, sent_by_staff_name = row
            recent_notifications.append(NotificationHistoryItem(
                notificationId=str(notification.notification_id),
                title=notification.title,
                body=notification.body,
                status=notification.notification_status,
                totalRequested=notification.total_requested,
                totalWithValidTokens=notification.total_with_valid_tokens,
                totalSentSuccessfully=notification.total_sent_successfully,
                totalFailed=notification.total_failed,
                sentAt=notification.sent_at,
                completedAt=notification.completed_at,
                createdAt=notification.created_at,
                sentByStaffName=sent_by_staff_name,
                errorMessage=notification.error_message,
                retryCount=notification.retry_count
            ))
        
        # Estimate unique students reached (simplified)
        students_reached_result = await db.execute(
            select(func.sum(Notification.total_sent_successfully))
            .where(Notification.college_id == college_id)
            .where(Notification.notification_status.in_(["sent", "partially_sent"]))
        )
        students_reached = students_reached_result.scalar() or 0
        
        statistics = NotificationStatistics(
            totalNotifications=total_notifications,
            successfulNotifications=status_counts.get("sent", 0),
            failedNotifications=status_counts.get("failed", 0),
            partiallySuccessfulNotifications=status_counts.get("partially_sent", 0),
            notificationsToday=notifications_today,
            notificationsThisWeek=notifications_this_week,
            notificationsThisMonth=notifications_this_month,
            studentsReached=students_reached,
            averageDeliveryRate=round(average_delivery_rate, 2),
            recentNotifications=recent_notifications
        )
        
        return NotificationStatisticsResponse(
            collegeName=college_name,
            statistics=statistics,
            generatedAt=datetime.now(timezone.utc)
        )
        
    except Exception as e:
        from app.core.utils import handle_api_exception
        handle_api_exception(e, "Get notification statistics", {"staff_id": str(current_staff.staff_id), "college_id": str(current_staff.college_id)}, status.HTTP_500_INTERNAL_SERVER_ERROR)