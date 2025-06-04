# Import all forms to make them available when importing from orders.forms
from .widgets import Select2Widget
from .order_form import OrderForm
from .order_item_form import OrderItemForm, OrderItemFormSet
from .order_status_form import OrderStatusUpdateForm
from .order_filter import OrderFilter, OrderFilterFormHelper
from .quick_order_form import QuickOrderForm
from .bulk_update_form import BulkStatusUpdateForm
from .order_item_filter_form import OrderItemFilterForm
from .order_summary_form import OrderSummaryForm
from .notification_preference_form import NotificationPreferenceForm
from .admin_notification_dashboard_filter_form import AdminNotificationDashboardFilterForm

# Make all forms available at the package level
__all__ = [
    'Select2Widget',
    'OrderForm',
    'OrderItemForm',
    'OrderItemFormSet',
    'OrderStatusUpdateForm',
    'OrderFilter',
    'OrderFilterFormHelper',
    'QuickOrderForm',
    'BulkStatusUpdateForm',
    'OrderItemFilterForm',
    'OrderSummaryForm',
    'NotificationPreferenceForm',
    'AdminNotificationDashboardFilterForm',
]
