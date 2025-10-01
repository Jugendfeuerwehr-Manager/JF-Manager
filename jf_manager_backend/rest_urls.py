from rest_framework import routers
from members.views import MemberViewSet, ParentViewSet
from users.views import UserViewSet
from orders.views import OrderViewSet, OrderableItemViewSet, OrderStatusViewSet, OrderItemViewSet
from qualifications.api_views import (
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
from servicebook.views import ServiceViewSet, AttandenceViewSet

api = routers.DefaultRouter()
api.register(r'users', UserViewSet)
api.register(r'members', MemberViewSet)
api.register(r'parents', ParentViewSet)


api.register(r'inventory/items', ItemViewSet)
api.register(r'inventory/categories', CategoryViewSet)
api.register(r'inventory/variants', ItemVariantViewSet)
api.register(r'inventory/locations', StorageLocationViewSet)
api.register(r'inventory/stocks', StockViewSet)
api.register(r'inventory/transactions', TransactionViewSet)


api.register(r'servicebook/services', ServiceViewSet)
api.register(r'servicebook/attandances', AttandenceViewSet)

# Orders endpoints
api.register(r'orders', OrderViewSet)
api.register(r'orders/items', OrderItemViewSet)
api.register(r'orders/orderable-items', OrderableItemViewSet)
api.register(r'orders/statuses', OrderStatusViewSet)

# Qualifications endpoints
api.register(r'qualifications/types', QualificationTypeViewSet)
api.register(r'qualifications', QualificationViewSet)
api.register(r'specialtasks/types', SpecialTaskTypeViewSet)
api.register(r'specialtasks', SpecialTaskViewSet)
