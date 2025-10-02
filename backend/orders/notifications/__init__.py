"""
JF-Manager Order Notification System

This package provides a comprehensive notification system for order management,
including email notifications, workflow management, and logging.

Architecture Overview:
- base.py: Base classes and common utilities
- email_service.py: Email notification handlers
- workflow_service.py: Order status workflow management
- template_service.py: Template rendering and management
- logging_service.py: Notification logging and tracking

Main Classes:
- OrderNotificationService: Main service for sending order-related notifications
- OrderWorkflowService: Service for handling order status workflows
- NotificationLogger: Service for logging notification activities
- TemplateRenderer: Service for rendering email templates

Usage:
    from orders.notifications import OrderNotificationService, OrderWorkflowService
    
    # Send order created notification
    OrderNotificationService.send_order_created_notification(order, request)
    
    # Check available status transitions
    transitions = OrderWorkflowService.get_available_transitions(current_status)
"""

from .email_service import OrderNotificationService
from .workflow_service import OrderWorkflowService
from .logging_service import NotificationLogger
from .template_service import TemplateRenderer

__all__ = [
    'OrderNotificationService',
    'OrderWorkflowService', 
    'NotificationLogger',
    'TemplateRenderer'
]

__version__ = '1.0.0'
