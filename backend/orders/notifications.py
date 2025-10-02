"""
Legacy compatibility module for the notification system.

This module provides backward compatibility by importing the refactored
notification services from the new package structure.

For new development, import directly from the notifications package:
    from orders.notifications import OrderNotificationService, OrderWorkflowService
"""

# Import all services from the new package structure for backward compatibility
from .notifications import (
    OrderNotificationService,
    OrderWorkflowService,
    NotificationLogger,
    TemplateRenderer
)

# Maintain the same interface for existing code
__all__ = ['OrderNotificationService', 'OrderWorkflowService']
