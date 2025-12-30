from rest_framework import routers
from members.api_views import (
    MemberViewSet, ParentViewSet, StatusViewSet, 
    GroupViewSet, EventViewSet, EventTypeViewSet, AttachmentViewSet
)
from members.api.viewsets.email_viewsets import EmailMessageViewSet
from users.api_views import UserViewSet
# Import enhanced API viewsets from orders.api instead of legacy orders.views
from orders.api.viewsets import (
    OrderViewSet, OrderableItemViewSet, OrderStatusViewSet, OrderItemViewSet
)
# Import enhanced qualifications viewsets from qualifications.api
from qualifications.api.viewsets import (
    QualificationTypeViewSet,
    QualificationViewSet,
    SpecialTaskTypeViewSet,
    SpecialTaskViewSet
)
"""Global REST API router registrations.

Inventory viewsets now sourced from `inventory.api.viewsets` instead of
`inventory.views` (legacy location). The old imports are kept working via
re-export for a short transition period.
"""

from inventory.api.viewsets import (
	ItemViewSet,
	CategoryViewSet,
	ItemVariantViewSet,
	StorageLocationViewSet,
	StockViewSet,
	TransactionViewSet,
)
# Import enhanced servicebook viewsets from servicebook.api
from servicebook.api.viewsets import ServiceViewSet, AttendanceViewSet
# Import settings viewset from settings_manager.api
from settings_manager.api import SettingsViewSet, EmailTemplateViewSet

api = routers.DefaultRouter()
api.register(r'users', UserViewSet)
api.register(r'members', MemberViewSet)
api.register(r'parents', ParentViewSet)
api.register(r'statuses', StatusViewSet)
api.register(r'groups', GroupViewSet)
api.register(r'events', EventViewSet)
api.register(r'event-types', EventTypeViewSet)
api.register(r'attachments', AttachmentViewSet)
api.register(r'emails', EmailMessageViewSet)


api.register(r'inventory/items', ItemViewSet)
api.register(r'inventory/categories', CategoryViewSet)
api.register(r'inventory/variants', ItemVariantViewSet)
api.register(r'inventory/locations', StorageLocationViewSet)
api.register(r'inventory/stocks', StockViewSet)
api.register(r'inventory/transactions', TransactionViewSet)


api.register(r'servicebook/services', ServiceViewSet)
api.register(r'servicebook/attendances', AttendanceViewSet)

# Orders endpoints
api.register(r'orders', OrderViewSet)
api.register(r'order-items', OrderItemViewSet)
api.register(r'orderable-items', OrderableItemViewSet)
api.register(r'order-statuses', OrderStatusViewSet)

# Qualifications endpoints - register most specific routes FIRST to avoid conflicts
# More specific routes must come before generic ones or they won't match
api.register(r'qualifications/types', QualificationTypeViewSet, basename='qualification-types')
api.register(r'qualifications/specialtask-types', SpecialTaskTypeViewSet, basename='qualification-specialtask-types')
api.register(r'qualifications/specialtasks', SpecialTaskViewSet, basename='qualification-specialtasks')
api.register(r'qualifications', QualificationViewSet, basename='qualifications')

# Settings endpoints
api.register(r'settings', SettingsViewSet, basename='settings')
api.register(r'settings/email-templates', EmailTemplateViewSet, basename='email-templates')
