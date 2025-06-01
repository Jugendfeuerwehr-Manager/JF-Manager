# Import all models to make them available when importing from orders.models
from .orders import (
    OrderStatus,
    OrderableItem,
    Order,
    OrderItem,
    OrderItemStatusHistory,
)

from .notifications import (
    NotificationPreference,
    NotificationLog,
    EmailTemplate,
)

# Make all models available at the package level
__all__ = [
    'OrderStatus',
    'OrderableItem', 
    'Order',
    'OrderItem',
    'OrderItemStatusHistory',
    'NotificationPreference',
    'NotificationLog',
    'EmailTemplate',
]
