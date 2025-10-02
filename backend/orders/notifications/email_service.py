"""
Email notification service for order management.

This module handles all email notification functionality including
order creation, status updates, bulk updates, reminders, and summaries.
"""

from django.core.mail import send_mail
from django.conf import settings
from django.utils.html import strip_tags
from collections import defaultdict
from typing import List, Dict, Any, Optional
import logging

from users.models import CustomUser
from ..models import Order, OrderItem, OrderStatus
from .base import BaseNotificationService, NotificationContext, RecipientError
from .template_service import TemplateRenderer
from .logging_service import NotificationLogger

logger = logging.getLogger(__name__)


class UserPreferencesChecker:
    """Helper class for checking user notification preferences."""
    
    PREFERENCE_MAP = {
        'order_created': 'email_new_orders',
        'status_update': 'email_status_updates', 
        'bulk_update': 'email_bulk_updates',
        'pending_reminder': 'email_pending_reminders',
    }
    
    @classmethod
    def check_user_preferences(cls, user, notification_type: str) -> bool:
        """
        Check if user wants to receive this type of notification.
        
        Args:
            user: User instance
            notification_type: Type of notification
            
        Returns:
            True if user wants to receive notification, False otherwise
        """
        try:
            if not hasattr(user, 'notification_preferences'):
                return True  # Default to sending if no preferences exist
            
            prefs = user.notification_preferences
            preference_attr = cls.PREFERENCE_MAP.get(notification_type)
            
            if preference_attr and hasattr(prefs, preference_attr):
                return getattr(prefs, preference_attr)
            
            return True  # Default to sending if preference not specified
            
        except Exception as e:
            logger.warning(f"Error checking user preferences: {e}")
            return True  # Default to sending on error


class RecipientCollector:
    """Helper class for collecting email recipients."""
    
    @staticmethod
    def get_admin_recipients(notification_type: str = None) -> List[str]:
        """
        Get list of admin email addresses.
        
        Args:
            notification_type: Type of notification for preference checking
            
        Returns:
            List of admin email addresses
        """
        try:
            admin_users = CustomUser.objects.filter(
                is_staff=True, 
                email__isnull=False
            ).exclude(email='')
            
            recipients = []
            for admin_user in admin_users:
                # Check user preferences if notification type specified
                if notification_type:
                    if not UserPreferencesChecker.check_user_preferences(
                        admin_user, notification_type
                    ):
                        continue
                
                recipients.append(admin_user.email)
            
            return recipients
            
        except Exception as e:
            logger.error(f"Failed to get admin recipients: {e}")
            return []
    
    @staticmethod
    def get_order_recipients(order: Order, notification_type: str = None) -> List[str]:
        """
        Get recipients for order-related notifications.
        
        Args:
            order: Order instance
            notification_type: Type of notification for preference checking
            
        Returns:
            List of email addresses
        """
        recipients = []
        
        try:
            # Add member email if available
            if hasattr(order.member, 'email') and order.member.email:
                recipients.append(order.member.email)
            
            # Add order creator email if different from member
            if (order.ordered_by and 
                order.ordered_by.email and 
                order.ordered_by.email not in recipients):
                
                # Check user preferences if notification type specified
                if notification_type:
                    if UserPreferencesChecker.check_user_preferences(
                        order.ordered_by, notification_type
                    ):
                        recipients.append(order.ordered_by.email)
                else:
                    recipients.append(order.ordered_by.email)
            
            return recipients
            
        except Exception as e:
            logger.error(f"Failed to get order recipients: {e}")
            return []


class OrderNotificationService(BaseNotificationService):
    """
    Main service for sending order-related email notifications.
    
    Handles all types of order notifications including creation, status updates,
    bulk updates, reminders, and summaries with comprehensive logging and
    error handling.
    """
    
    @classmethod
    def send_order_created_notification(cls, order: Order, request=None) -> bool:
        """
        Send notification when new order is created.
        
        Args:
            order: Order instance that was created
            request: Django request object (optional)
            
        Returns:
            True if at least one notification was sent successfully
        """
        try:
            # Build notification context
            context = (NotificationContext(request)
                      .add_order_context(order)
                      .add_custom(items=order.items.all())
                      .build())
            
            # Render email content
            subject, html_message, plain_message = TemplateRenderer.render_email_content(
                'order_created', context
            )
            
            # Get admin recipients
            recipients = RecipientCollector.get_admin_recipients('order_created')
            
            if not recipients:
                logger.warning("No admin recipients found for order created notification")
                return False
            
            return cls._send_to_recipients(
                recipients=recipients,
                subject=subject,
                html_message=html_message,
                plain_message=plain_message,
                notification_type='order_created',
                order=order
            )
            
        except Exception as e:
            logger.error(f"Failed to send order created notification: {e}")
            return False
    
    @classmethod
    def send_status_update_notification(
        cls, 
        order_item: OrderItem, 
        old_status: OrderStatus, 
        new_status: OrderStatus, 
        updated_by, 
        request=None
    ) -> bool:
        """
        Send notification when order item status changes.
        
        Args:
            order_item: OrderItem that was updated
            old_status: Previous OrderStatus
            new_status: New OrderStatus  
            updated_by: User who made the change
            request: Django request object (optional)
            
        Returns:
            True if at least one notification was sent successfully
        """
        try:
            # Build notification context
            context = (NotificationContext(request)
                      .add_order_context(order_item.order)
                      .add_order_item_context(order_item)
                      .add_status_context(old_status, new_status, updated_by)
                      .build())
            
            # Render email content
            subject, html_message, plain_message = TemplateRenderer.render_email_content(
                'status_update', context
            )
            
            # Get recipients (member and order creator)
            recipients = RecipientCollector.get_order_recipients(
                order_item.order, 'status_update'
            )
            
            if not recipients:
                logger.info("No recipients found for status update notification")
                return True  # Not an error if no one wants notifications
            
            return cls._send_to_recipients(
                recipients=recipients,
                subject=subject,
                html_message=html_message,
                plain_message=plain_message,
                notification_type='status_update',
                order=order_item.order,
                order_item=order_item
            )
            
        except Exception as e:
            logger.error(f"Failed to send status update notification: {e}")
            return False
    
    @classmethod
    def send_bulk_status_update_notification(
        cls, 
        order_items: List[OrderItem], 
        new_status: OrderStatus, 
        updated_by, 
        request=None
    ) -> bool:
        """
        Send notification for bulk status updates.
        
        Args:
            order_items: List of OrderItem instances that were updated
            new_status: New OrderStatus applied to all items
            updated_by: User who made the changes
            request: Django request object (optional)
            
        Returns:
            True if notifications were sent successfully
        """
        try:
            # Group items by order
            orders_dict = cls._group_items_by_order(order_items)
            
            success_count = 0
            
            # Send notification for each order
            for order_data in orders_dict.values():
                try:
                    # Build notification context for this order
                    context = (NotificationContext(request)
                              .add_order_context(order_data['order'])
                              .add_status_context(new_status=new_status, updated_by=updated_by)
                              .add_custom(items=order_data['items'])
                              .build())
                    
                    # Render email content
                    subject, html_message, plain_message = TemplateRenderer.render_email_content(
                        'bulk_update', context
                    )
                    
                    # Get recipients for this order
                    recipients = RecipientCollector.get_order_recipients(
                        order_data['order'], 'bulk_update'
                    )
                    
                    if recipients:
                        if cls._send_to_recipients(
                            recipients=recipients,
                            subject=subject,
                            html_message=html_message,
                            plain_message=plain_message,
                            notification_type='bulk_update',
                            order=order_data['order']
                        ):
                            success_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to send bulk update notification for order {order_data['order'].pk}: {e}")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Failed to send bulk status update notification: {e}")
            return False
    
    @classmethod
    def send_pending_order_reminder(
        cls, 
        order: Order, 
        pending_items: List[OrderItem], 
        request=None
    ) -> bool:
        """
        Send reminder notification for pending order items.
        
        Args:
            order: Order with pending items
            pending_items: List of OrderItem instances that are pending
            request: Django request object (optional)
            
        Returns:
            True if notification was sent successfully
        """
        try:
            # Build notification context
            context = (NotificationContext(request)
                      .add_order_context(order)
                      .add_custom(pending_items=pending_items)
                      .build())
            
            # Render email content
            subject, html_message, plain_message = TemplateRenderer.render_email_content(
                'pending_reminder', context
            )
            
            # Get admin recipients
            recipients = RecipientCollector.get_admin_recipients('pending_reminder')
            
            if not recipients:
                logger.warning("No admin recipients found for pending order reminder")
                return False
            
            return cls._send_to_recipients(
                recipients=recipients,
                subject=subject,
                html_message=html_message,
                plain_message=plain_message,
                notification_type='pending_reminder',
                order=order
            )
            
        except Exception as e:
            logger.error(f"Failed to send pending order reminder: {e}")
            return False
    
    @classmethod
    def send_order_summary_notification(
        cls,
        recipient_email: str, 
        orders, 
        filters: Optional[Dict] = None, 
        request=None
    ) -> bool:
        """
        Send order summary notification to external personnel.
        
        Args:
            recipient_email: Email address of recipient
            orders: QuerySet or list of Order instances
            filters: Optional filters applied to the summary
            request: Django request object (optional)
            
        Returns:
            True if notification was sent successfully
        """
        try:
            # Process orders data for summary
            summary_data = cls._process_orders_for_summary(orders)
            
            # Build notification context
            context = (NotificationContext(request)
                      .add_custom(
                          orders=orders,
                          grouped_items=summary_data['grouped_items'],
                          shopping_list=summary_data['shopping_list'],
                          total_items=summary_data['total_items'],
                          **cls._build_filter_context(filters)
                      )
                      .build())
            
            # Render email content
            subject, html_message, plain_message = TemplateRenderer.render_email_content(
                'order_summary', context
            )
            
            return cls._send_to_recipients(
                recipients=[recipient_email],
                subject=subject,
                html_message=html_message,
                plain_message=plain_message,
                notification_type='order_summary'
            )
            
        except Exception as e:
            logger.error(f"Failed to send order summary notification: {e}")
            return False
    
    @classmethod
    def _send_to_recipients(
        cls,
        recipients: List[str],
        subject: str,
        html_message: str,
        plain_message: str,
        notification_type: str,
        order: Optional[Order] = None,
        order_item: Optional[OrderItem] = None
    ) -> bool:
        """
        Send email to list of recipients with logging.
        
        Args:
            recipients: List of email addresses
            subject: Email subject
            html_message: HTML email content
            plain_message: Plain text email content
            notification_type: Type of notification for logging
            order: Related order (optional)
            order_item: Related order item (optional)
            
        Returns:
            True if at least one email was sent successfully
        """
        if not recipients:
            raise RecipientError("No recipients provided")
        
        success_count = 0
        
        for recipient_email in recipients:
            # Create log entry
            log_entry = NotificationLogger.create_log_entry(
                notification_type=notification_type,
                recipient_email=recipient_email,
                subject=subject,
                order=order,
                order_item=order_item
            )
            
            try:
                send_mail(
                    subject=subject,
                    message=plain_message,
                    html_message=html_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient_email],
                    fail_silently=False,
                )
                
                NotificationLogger.mark_as_sent(log_entry)
                success_count += 1
                
            except Exception as e:
                NotificationLogger.mark_as_failed(log_entry, str(e))
                logger.error(f"Failed to send email to {recipient_email}: {e}")
        
        return success_count > 0
    
    @classmethod
    def _group_items_by_order(cls, order_items: List[OrderItem]) -> Dict:
        """Group order items by their parent order."""
        orders_dict = {}
        
        for item in order_items:
            order_pk = item.order.pk
            if order_pk not in orders_dict:
                orders_dict[order_pk] = {
                    'order': item.order,
                    'items': []
                }
            orders_dict[order_pk]['items'].append(item)
        
        return orders_dict
    
    @classmethod
    def _process_orders_for_summary(cls, orders) -> Dict:
        """Process orders data for summary email template."""
        grouped_items = defaultdict(list)
        shopping_list = defaultdict(lambda: {
            'item_name': '',
            'category': '',
            'sizes': defaultdict(int),
            'total_quantity': 0,
            'statuses': set(),
            'order_items': []
        })
        
        total_items = 0
        
        # Process all order items
        for order in orders:
            for item in order.items.all():
                total_items += item.quantity
                
                # Group by category
                category = item.item.category or 'Keine Kategorie'
                
                # Find existing item data in grouped_items
                item_found = False
                for existing_item in grouped_items[category]:
                    if existing_item['item'] == item.item:
                        existing_item['order_items'].append(item)
                        existing_item['total_quantity'] += item.quantity
                        item_found = True
                        break
                
                if not item_found:
                    grouped_items[category].append({
                        'item': item.item,
                        'order_items': [item],
                        'total_quantity': item.quantity
                    })
                
                # Build shopping list summary
                item_key = f"{item.item.name}_{item.item.category}"
                shopping_item = shopping_list[item_key]
                shopping_item['item_name'] = item.item.name
                shopping_item['category'] = item.item.category
                shopping_item['total_quantity'] += item.quantity
                shopping_item['statuses'].add(item.status.name)
                shopping_item['order_items'].append(item)
                
                size_key = item.size if item.size else 'Keine'
                shopping_item['sizes'][size_key] += item.quantity
        
        # Convert shopping_list to list and sort
        shopping_list_final = []
        for item_data in shopping_list.values():
            item_data['statuses'] = list(item_data['statuses'])
            # Convert defaultdict to regular dict for Django template compatibility
            item_data['sizes'] = dict(item_data['sizes'])
            shopping_list_final.append(item_data)
        
        shopping_list_final.sort(key=lambda x: (x['category'] or 'ZZZ', x['item_name']))
        
        return {
            'grouped_items': dict(grouped_items),
            'shopping_list': shopping_list_final,
            'total_items': total_items
        }
    
    @classmethod
    def _build_filter_context(cls, filters: Optional[Dict]) -> Dict:
        """Build context variables from filters."""
        if not filters:
            return {
                'date_from': None,
                'date_to': None,
                'status_filter': None,
                'include_notes': True,
                'group_by_category': True,
                'additional_notes': '',
            }
        
        return {
            'date_from': filters.get('date_from'),
            'date_to': filters.get('date_to'),
            'status_filter': list(filters.get('status_filter', [])) if filters.get('status_filter') else None,
            'include_notes': filters.get('include_notes', True),
            'group_by_category': filters.get('group_by_category', True),
            'additional_notes': filters.get('additional_notes', ''),
        }
