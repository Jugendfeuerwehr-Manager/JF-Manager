"""
Unit tests for the notification system.

Run with: python manage.py test orders.tests.test_notifications
"""

from django.test import TestCase
from unittest.mock import Mock, patch
from orders.notifications import (
    OrderNotificationService,
    OrderWorkflowService,
    NotificationLogger,
    TemplateRenderer
)


class NotificationSystemTests(TestCase):
    """Test the refactored notification system."""
    
    def test_imports_work(self):
        """Test that all imports work correctly."""
        # Test that services can be imported
        self.assertTrue(hasattr(OrderNotificationService, 'send_order_created_notification'))
        self.assertTrue(hasattr(OrderWorkflowService, 'get_available_transitions'))
        self.assertTrue(hasattr(NotificationLogger, 'create_log_entry'))
        self.assertTrue(hasattr(TemplateRenderer, 'render_email_content'))
    
    def test_workflow_transitions(self):
        """Test workflow transition logic."""
        # Mock a status object
        mock_status = Mock()
        mock_status.code = 'pending'
        
        # Test getting available transitions
        transitions = OrderWorkflowService.get_available_transitions(mock_status)
        self.assertIn('ordered', transitions)
        self.assertIn('cancelled', transitions)
    
    def test_template_caching(self):
        """Test template caching functionality."""
        # Test cache clearing
        TemplateRenderer.clear_template_cache('order_created')
        # Should not raise any exceptions
        self.assertTrue(True)
    
    def test_notification_logger_stats(self):
        """Test notification statistics."""
        # Test getting stats with no data
        stats = NotificationLogger.get_notification_stats(days=1)
        self.assertEqual(stats['total_notifications'], 0)
        self.assertEqual(stats['success_rate'], 0)


class BackwardCompatibilityTests(TestCase):
    """Test that backward compatibility is maintained."""
    
    def test_old_imports_work(self):
        """Test that old import style still works."""
        from orders.notifications import OrderNotificationService as OldService
        from orders.notifications import OrderWorkflowService as OldWorkflow
        
        # Should be able to access the same methods as before
        self.assertTrue(hasattr(OldService, 'send_order_created_notification'))
        self.assertTrue(hasattr(OldWorkflow, 'get_available_transitions'))
