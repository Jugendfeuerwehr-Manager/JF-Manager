"""
Base classes and common utilities for the notification system.

This module provides base functionality and common utilities used across
the notification system.
"""

from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class BaseNotificationService(ABC):
    """
    Abstract base class for notification services.
    
    Provides common functionality for all notification services including
    domain resolution, URL generation, and error handling.
    """
    
    @staticmethod
    def get_domain_info(request=None):
        """
        Get domain and protocol information for generating absolute URLs.
        
        Args:
            request: Django request object (optional)
            
        Returns:
            tuple: (domain, protocol) for URL generation
        """
        if request:
            domain = request.get_host()
            protocol = 'https' if request.is_secure() else 'http'
        else:
            # Default for development/testing
            domain = getattr(settings, 'DEFAULT_DOMAIN', 'localhost:8000')
            protocol = getattr(settings, 'DEFAULT_PROTOCOL', 'http')
        
        return domain, protocol
    
    @staticmethod
    def build_absolute_url(path, request=None):
        """
        Build an absolute URL for the given path.
        
        Args:
            path: URL path (e.g., from reverse())
            request: Django request object (optional)
            
        Returns:
            str: Complete absolute URL
        """
        domain, protocol = BaseNotificationService.get_domain_info(request)
        return f"{protocol}://{domain}{path}"
    
    @staticmethod
    def safe_execute(func, *args, error_message="Operation failed", **kwargs):
        """
        Safely execute a function with error handling and logging.
        
        Args:
            func: Function to execute
            *args: Function arguments
            error_message: Error message prefix for logging
            **kwargs: Function keyword arguments
            
        Returns:
            bool: True if successful, False if failed
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"{error_message}: {e}")
            return False


class NotificationContext:
    """
    Helper class for building notification contexts.
    
    Provides a consistent way to build context dictionaries for email templates.
    """
    
    def __init__(self, request=None):
        """
        Initialize notification context builder.
        
        Args:
            request: Django request object (optional)
        """
        self.request = request
        self.domain, self.protocol = BaseNotificationService.get_domain_info(request)
        self._context = {
            'domain': self.domain,
            'protocol': self.protocol,
            'timestamp': timezone.now(),
        }
    
    def add_order_context(self, order):
        """Add order-related context."""
        self._context.update({
            'order': order,
            'member': order.member,
            'order_url': self._build_order_url(order),
        })
        return self
    
    def add_order_item_context(self, order_item):
        """Add order item-related context."""
        self._context.update({
            'order_item': order_item,
            'item': order_item.item,
        })
        return self
    
    def add_status_context(self, old_status=None, new_status=None, updated_by=None):
        """Add status change context."""
        self._context.update({
            'old_status': old_status,
            'new_status': new_status,
            'updated_by': updated_by,
        })
        return self
    
    def add_custom(self, **kwargs):
        """Add custom context variables."""
        self._context.update(kwargs)
        return self
    
    def build(self):
        """Build and return the context dictionary."""
        return self._context.copy()
    
    def _build_order_url(self, order):
        """Build absolute URL for order detail page."""
        path = reverse('orders:detail', kwargs={'pk': order.pk})
        return f"{self.protocol}://{self.domain}{path}"


class NotificationError(Exception):
    """Custom exception for notification-related errors."""
    pass


class TemplateNotFoundError(NotificationError):
    """Exception raised when a required template is not found."""
    pass


class RecipientError(NotificationError):
    """Exception raised when there are issues with email recipients."""
    pass
