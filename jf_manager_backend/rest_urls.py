from rest_framework import routers
from members.views import MemberViewSet, ParentViewSet
from inventory.views import ItemViewSet, CategoryViewSet
from servicebook.views import ServiceViewSet, AttandenceViewSet

api = routers.DefaultRouter()
api.register(r'members', MemberViewSet)
api.register(r'parents', ParentViewSet)


api.register(r'inventory/items', ItemViewSet)
api.register(r'inventory/categories', CategoryViewSet)


api.register(r'servicebook/services', ServiceViewSet)
api.register(r'servicebook/attandances', AttandenceViewSet)
