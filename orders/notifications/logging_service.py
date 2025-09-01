
"""
Notification logging service for tracking email activities.

This module handles logging of notification activities, tracking delivery
status, and providing audit trails for email notifications.
"""

from django.utils import timezone
from typing import Optional, List, Dict, Any
import logging

from ..models import NotificationLog, Order, OrderItem
from .base import BaseNotificationService

logger = logging.getLogger(__name__)


class NotificationLogger(BaseNotificationService):
    """
    Service for logging and tracking notification activities.
    
    Provides comprehensive logging for email notifications including
    delivery status tracking, error logging, and audit trails.
    """
    
    NOTIFICATION_TYPES = {
        'order_created': 'Order Created',
        'status_update': 'Status Update', 
        'bulk_update': 'Bulk Status Update',
        'pending_reminder': 'Pending Reminder',
        'order_summary': 'Order Summary'
    }
    
    @classmethod
    def create_log_entry(
        cls,
        notification_type: str,
        recipient_email: str,
        subject: str,
        order: Optional[Order] = None,
        order_item: Optional[OrderItem] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> NotificationLog:
        """
        Create a new notification log entry.
        
        Args:
            notification_type: Type of notification being sent
            recipient_email: Email address of recipient
            subject: Email subject line
            order: Related order (optional)
            order_item: Related order item (optional)
            additional_data: Additional metadata (optional)
            
        Returns:
            NotificationLog instance
        """
        try:
            log_entry = NotificationLog.objects.create(
                notification_type=notification_type,
                recipient_email=recipient_email,
                subject=subject,
                order=order,
                order_item=order_item,
                status='pending',
                additional_data=additional_data or {}
            )
            
            logger.info(
                f"Created notification log entry {log_entry.id} for {notification_type} "
                f"to {recipient_email}"
            )
            
            return log_entry
            
        except Exception as e:
            logger.error(f"Failed to create notification log entry: {e}")
            raise
    
    @classmethod
    def mark_as_sent(cls, log_entry: NotificationLog, delivery_info: Optional[Dict] = None):
        """
        Mark a notification log entry as successfully sent.
        
        Args:
            log_entry: NotificationLog instance to update
            delivery_info: Optional delivery information
        """
        try:
            log_entry.status = 'sent'
            log_entry.sent_at = timezone.now()
            
            if delivery_info:
                log_entry.additional_data.update({'delivery_info': delivery_info})
            
            log_entry.save()
            
            logger.info(f"Marked notification log entry {log_entry.id} as sent")
            
        except Exception as e:
            logger.error(f"Failed to mark notification as sent: {e}")
    
    @classmethod
    def mark_as_failed(cls, log_entry: NotificationLog, error_message: str):
        """
        Mark a notification log entry as failed.
        
        Args:
            log_entry: NotificationLog instance to update
            error_message: Error description
        """
        try:
            log_entry.status = 'failed'
            log_entry.error_message = error_message
            log_entry.failed_at = timezone.now()
            log_entry.save()
            
            logger.error(
                f"Marked notification log entry {log_entry.id} as failed: {error_message}"
            )
            
        except Exception as e:
            logger.error(f"Failed to mark notification as failed: {e}")
    
    @classmethod
    def get_notification_history(
        cls,
        order: Optional[Order] = None,
        recipient_email: Optional[str] = None,
        notification_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[NotificationLog]:
        """
        Get notification history with optional filtering.
        
        Args:
            order: Filter by specific order
            recipient_email: Filter by recipient email
            notification_type: Filter by notification type
            status: Filter by status ('pending', 'sent', 'failed')
            limit: Maximum number of results
            
        Returns:
            List of NotificationLog instances
        """
        queryset = NotificationLog.objects.all()
        
        if order:
            queryset = queryset.filter(order=order)
        
        if recipient_email:
            queryset = queryset.filter(recipient_email=recipient_email)
        
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        if status:
            queryset = queryset.filter(status=status)
        
        return list(queryset.order_by('-created_at')[:limit])
    
    @classmethod
    def get_failed_notifications(cls, hours: int = 24) -> List[NotificationLog]:
        """
        Get failed notifications within specified time window.
        
        Args:
            hours: Time window in hours to look back
            
        Returns:
            List of failed NotificationLog instances
        """
        cutoff_time = timezone.now() - timezone.timedelta(hours=hours)
        
        return list(
            NotificationLog.objects.filter(
                status='failed',
                created_at__gte=cutoff_time
            ).order_by('-created_at')
        )
    
    @classmethod
    def get_notification_stats(cls, days: int = 30) -> Dict[str, Any]:
        """
        Get notification statistics for the specified period.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with notification statistics
        """
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        
        queryset = NotificationLog.objects.filter(created_at__gte=cutoff_date)
        
        total_notifications = queryset.count()
        sent_notifications = queryset.filter(status='sent').count()
        failed_notifications = queryset.filter(status='failed').count()
        pending_notifications = queryset.filter(status='pending').count()
        
        # Get stats by notification type
        type_stats = {}
        for notification_type, display_name in cls.NOTIFICATION_TYPES.items():
            type_count = queryset.filter(notification_type=notification_type).count()
            type_stats[notification_type] = {
                'display_name': display_name,
                'count': type_count
            }
        
        success_rate = (sent_notifications / total_notifications * 100) if total_notifications > 0 else 0
        
        return {
            'period_days': days,
            'total_notifications': total_notifications,
            'sent_notifications': sent_notifications,
            'failed_notifications': failed_notifications,
            'pending_notifications': pending_notifications,
            'success_rate': round(success_rate, 2),
            'type_breakdown': type_stats
        }
    
    @classmethod
    def retry_failed_notification(cls, log_entry: NotificationLog) -> bool:
        """
        Retry a failed notification.
        
        Args:
            log_entry: Failed NotificationLog instance to retry
            
        Returns:
            True if retry was initiated successfully
        """
        if log_entry.status != 'failed':
            logger.warning(f"Cannot retry notification {log_entry.id} - status is not 'failed'")
            return False
        
        try:
            # Reset status to pending for retry
            log_entry.status = 'pending'
            log_entry.error_message = ''
            log_entry.failed_at = None
            log_entry.save()
            
            logger.info(f"Reset notification {log_entry.id} for retry")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset notification for retry: {e}")
            return False
    
    @classmethod
    def cleanup_old_logs(cls, days: int = 90) -> int:
        """
        Clean up old notification logs to manage database size.
        
        Args:
            days: Number of days to keep logs
            
        Returns:
            Number of deleted log entries
        """
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        
        try:
            deleted_count, _ = NotificationLog.objects.filter(
                created_at__lt=cutoff_date
            ).delete()
            
            logger.info(f"Cleaned up {deleted_count} old notification logs")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old logs: {e}")
            return 0
