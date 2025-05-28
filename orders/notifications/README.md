# JF-Manager Notification System Architecture

## Overview

The JF-Manager notification system has been refactored into a modular, maintainable architecture that separates concerns and provides comprehensive email notification functionality for order management.

## Architecture Principles

- **Single Responsibility**: Each module handles a specific aspect of notifications
- **Separation of Concerns**: Business logic, template rendering, logging, and email sending are separated
- **Dependency Injection**: Services depend on abstractions rather than concrete implementations
- **Error Handling**: Comprehensive error handling and logging throughout
- **Testability**: Modular design makes unit testing easier
- **Extensibility**: Easy to add new notification types or modify existing ones

## Module Structure

```
orders/notifications/
├── __init__.py                 # Package initialization and exports
├── base.py                     # Base classes and common utilities
├── email_service.py           # Main email notification service
├── workflow_service.py        # Order status workflow management
├── template_service.py        # Email template rendering and caching
├── logging_service.py         # Notification logging and tracking
└── README.md                  # This documentation
```

## Core Components

### 1. Base Module (`base.py`)

**Purpose**: Provides foundational classes and utilities used across the notification system.

**Key Classes**:
- `BaseNotificationService`: Abstract base class with common functionality
- `NotificationContext`: Helper for building email template contexts
- `NotificationError`: Custom exception hierarchy

**Key Features**:
- Domain and URL resolution for absolute links
- Safe execution wrapper with error handling
- Context building utilities
- Custom exception classes

### 2. Email Service (`email_service.py`)

**Purpose**: Main service for sending order-related email notifications.

**Key Classes**:
- `OrderNotificationService`: Main notification service
- `UserPreferencesChecker`: Utility for checking user notification preferences
- `RecipientCollector`: Utility for collecting email recipients

**Notification Types**:
- Order creation notifications
- Status update notifications
- Bulk status update notifications
- Pending order reminders
- Order summary notifications

**Key Features**:
- User preference checking
- Recipient collection and validation
- Comprehensive error handling and logging
- Template rendering integration
- Bulk operation support

### 3. Workflow Service (`workflow_service.py`)

**Purpose**: Manages order status workflows and transitions.

**Key Classes**:
- `OrderWorkflowService`: Status workflow management

**Key Features**:
- Status transition validation
- Workflow diagram data generation
- Status categorization (active, completed, terminated, etc.)
- Bulk transition validation
- Status statistics calculation

**Status Categories**:
- `active`: pending, ordered, received, ready
- `completed`: delivered
- `terminated`: cancelled, defective
- `actionable`: pending, ordered, defective
- `final`: delivered, cancelled

### 4. Template Service (`template_service.py`)

**Purpose**: Handles email template rendering, caching, and management.

**Key Classes**:
- `TemplateRenderer`: Template rendering with caching

**Key Features**:
- Custom template support from database
- Fallback to default file templates
- Template caching for performance
- Subject line template rendering
- HTML and plain text generation

**Template Types**:
- `order_created`: New order notifications
- `status_update`: Status change notifications
- `bulk_update`: Bulk status changes
- `pending_reminder`: Pending item reminders
- `order_summary`: Order summary reports

### 5. Logging Service (`logging_service.py`)

**Purpose**: Comprehensive logging and tracking of notification activities.

**Key Classes**:
- `NotificationLogger`: Notification logging and tracking

**Key Features**:
- Delivery status tracking
- Error logging and retry functionality
- Notification history and statistics
- Audit trail maintenance
- Cleanup utilities for old logs

**Log Statuses**:
- `pending`: Notification queued for sending
- `sent`: Successfully delivered
- `failed`: Delivery failed with error details

## Usage Examples

### Basic Usage

```python
from orders.notifications import OrderNotificationService, OrderWorkflowService

# Send order created notification
success = OrderNotificationService.send_order_created_notification(order, request)

# Check available status transitions
transitions = OrderWorkflowService.get_available_transitions(current_status)

# Send status update notification
OrderNotificationService.send_status_update_notification(
    order_item, old_status, new_status, updated_by, request
)
```

### Advanced Usage

```python
from orders.notifications import NotificationLogger, TemplateRenderer

# Get notification statistics
stats = NotificationLogger.get_notification_stats(days=30)

# Render custom email template
subject, html, plain = TemplateRenderer.render_email_content(
    'order_created', context
)

# Validate bulk status transition
validation = OrderWorkflowService.validate_bulk_transition(
    order_items, target_status
)
```

## Configuration

### Settings

The notification system respects the following Django settings:

```python
# Email settings
DEFAULT_FROM_EMAIL = 'noreply@jf-manager.example.com'

# Default domain for URL generation (development)
DEFAULT_DOMAIN = 'localhost:8000'
DEFAULT_PROTOCOL = 'http'

# Cache settings for template caching
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

### User Preferences

Users can control which notifications they receive through notification preferences:

```python
class NotificationPreferences(models.Model):
    user = models.OneToOneField(User, related_name='notification_preferences')
    email_new_orders = models.BooleanField(default=True)
    email_status_updates = models.BooleanField(default=True)
    email_bulk_updates = models.BooleanField(default=True)
    email_pending_reminders = models.BooleanField(default=True)
```

## Error Handling

The notification system implements comprehensive error handling:

1. **Individual Email Failures**: Failed emails are logged but don't prevent other emails from being sent
2. **Template Errors**: Fallback to default templates if custom templates fail
3. **Recipient Errors**: Graceful handling of invalid or missing email addresses
4. **Logging Failures**: Errors are logged to Django's logging system
5. **Retry Mechanism**: Failed notifications can be retried through the logging service

## Performance Considerations

### Template Caching

Email templates are cached to improve performance:
- Custom templates from database are cached for 1 hour
- Cache invalidation when templates are updated
- Separate cache entries for each template type

### Bulk Operations

The system is optimized for bulk operations:
- Bulk status updates are grouped by order
- Single database queries where possible
- Efficient recipient collection

### Database Queries

- Use of `select_related` and `prefetch_related` for efficient querying
- Batch processing for large datasets
- Pagination support for large result sets

## Testing Strategy

### Unit Tests

Each module should have comprehensive unit tests:

```python
# Example test structure
tests/
├── test_email_service.py
├── test_workflow_service.py
├── test_template_service.py
├── test_logging_service.py
└── test_integration.py
```

### Test Categories

1. **Unit Tests**: Test individual methods and classes
2. **Integration Tests**: Test interaction between modules
3. **Email Tests**: Test actual email sending (with mock backends)
4. **Template Tests**: Test template rendering with various contexts
5. **Workflow Tests**: Test status transition logic

## Migration Guide

### From Old System

To migrate from the old monolithic `notifications.py`:

1. **Update Imports**:
   ```python
   # Old
   from orders.notifications import OrderNotificationService
   
   # New (same interface)
   from orders.notifications import OrderNotificationService
   ```

2. **Update Template Paths**: Ensure email templates exist in expected locations
3. **Update Settings**: Add new configuration options if needed
4. **Test Thoroughly**: Verify all notification types work correctly

### Backward Compatibility

The new system maintains backward compatibility with the existing API:
- All public methods have the same signatures
- Same return values and behavior
- Existing email templates continue to work

## Future Enhancements

### Planned Features

1. **Queue Support**: Integration with Celery for asynchronous email sending
2. **Multiple Channels**: SMS, push notifications, etc.
3. **Template Editor**: Web-based template editing interface
4. **Analytics Dashboard**: Notification metrics and analytics
5. **A/B Testing**: Template variation testing
6. **Internationalization**: Multi-language template support

### Extension Points

The architecture provides several extension points:

1. **Custom Notification Types**: Add new notification types by extending services
2. **Custom Template Backends**: Implement custom template storage/rendering
3. **Custom Logging Backends**: Integrate with external logging/monitoring systems
4. **Custom Recipient Sources**: Add new sources for email recipients

## Monitoring and Maintenance

### Health Checks

Monitor the notification system health:

```python
from orders.notifications import NotificationLogger

# Check for failed notifications
failed_notifications = NotificationLogger.get_failed_notifications(hours=24)

# Get system statistics
stats = NotificationLogger.get_notification_stats(days=7)
```

### Maintenance Tasks

Regular maintenance tasks:

1. **Log Cleanup**: Clean old notification logs periodically
2. **Cache Warming**: Pre-warm template caches if needed
3. **Statistics Review**: Monitor notification success rates
4. **Template Updates**: Keep default templates updated

### Troubleshooting

Common issues and solutions:

1. **Templates Not Found**: Check template paths and file permissions
2. **Email Not Sending**: Verify email settings and SMTP configuration
3. **User Preferences**: Check user notification preference settings
4. **Status Transitions**: Verify workflow configuration is correct

---

For additional support or questions, please refer to the inline documentation in each module or contact the development team.
