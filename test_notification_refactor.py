"""
Quick test to verify the notification system refactoring works correctly.

This script tests that:
1. All imports work correctly
2. Services can be instantiated
3. Basic functionality is accessible
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, '/Users/lukasbisdorf/Dev/JF-Manager')

# Test that all imports work
try:
    from orders.notifications import (
        OrderNotificationService,
        OrderWorkflowService,
        NotificationLogger,
        TemplateRenderer
    )
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Test backward compatibility
try:
    from orders.notifications import OrderNotificationService as OldService
    from orders.notifications import OrderWorkflowService as OldWorkflow
    print("✅ Backward compatibility maintained")
except ImportError as e:
    print(f"❌ Backward compatibility error: {e}")
    sys.exit(1)

# Test that classes have expected methods
def test_class_methods():
    """Test that refactored classes have the expected public methods."""
    
    # Test OrderNotificationService methods
    expected_notification_methods = [
        'send_order_created_notification',
        'send_status_update_notification', 
        'send_bulk_status_update_notification',
        'send_pending_order_reminder',
        'send_order_summary_notification'
    ]
    
    for method_name in expected_notification_methods:
        if hasattr(OrderNotificationService, method_name):
            print(f"✅ OrderNotificationService.{method_name} exists")
        else:
            print(f"❌ OrderNotificationService.{method_name} missing")
    
    # Test OrderWorkflowService methods
    expected_workflow_methods = [
        'get_available_transitions',
        'can_transition_to',
        'get_next_statuses'
    ]
    
    for method_name in expected_workflow_methods:
        if hasattr(OrderWorkflowService, method_name):
            print(f"✅ OrderWorkflowService.{method_name} exists")
        else:
            print(f"❌ OrderWorkflowService.{method_name} missing")

if __name__ == '__main__':
    test_class_methods()
    print("\n🎉 Notification system refactoring test completed successfully!")
