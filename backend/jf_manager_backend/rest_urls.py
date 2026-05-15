from rest_framework import routers

from departments.api.viewsets.departments import DepartmentViewSet
from departments.api.viewsets.user_department_roles import UserDepartmentRoleViewSet
from external_sync.api import SyncJobViewSet, SyncRunViewSet
from inventory.api import (
    CategoryViewSet,
    ItemVariantViewSet,
    ItemViewSet,
    StockViewSet,
    StorageLocationViewSet,
    TransactionViewSet,
)
from members.api.viewsets import (
    AttachmentViewSet,
    EmailMessageViewSet,
    EventTypeViewSet,
    EventViewSet,
    GroupViewSet,
    MemberListViewSet,
    MemberViewSet,
    ParentViewSet,
    StatusViewSet,
)
from orders.api.viewsets import OrderableItemViewSet, OrderItemViewSet, OrderStatusViewSet, OrderViewSet
from qualifications.api.viewsets import (
    QualificationTypeViewSet,
    QualificationViewSet,
    SpecialTaskTypeViewSet,
    SpecialTaskViewSet,
)
from servicebook.api.viewsets import AttendanceViewSet, ServiceViewSet
from settings_manager.api import (
    EmailLayoutTemplateViewSet,
    EmailTemplateViewSet,
    LDAPDepartmentMappingViewSet,
    OIDCGroupMappingViewSet,
    SettingsViewSet,
)
from training.api.viewsets import (
    LibraryBlockCategoryViewSet,
    LibraryBlockTagViewSet,
    LibraryBlockViewSet,
    TrainingBlockViewSet,
    TrainingSessionViewSet,
)
from users.api.viewsets.admin_viewsets import AdminUserViewSet, AuthGroupViewSet, PermissionViewSet
from users.api_views import UserViewSet

api = routers.DefaultRouter()
api.register(r"users", UserViewSet)
api.register(r"admin/users", AdminUserViewSet, basename="admin-users")
api.register(r"admin/groups", AuthGroupViewSet, basename="admin-groups")
api.register(r"admin/permissions", PermissionViewSet, basename="admin-permissions")

# Department management
api.register(r"departments", DepartmentViewSet, basename="departments")
api.register(r"admin/department-roles", UserDepartmentRoleViewSet, basename="department-roles")
api.register(r"sync-jobs", SyncJobViewSet, basename="sync-jobs")
api.register(r"sync-runs", SyncRunViewSet, basename="sync-runs")
api.register(r"members", MemberViewSet)
api.register(r"parents", ParentViewSet)
api.register(r"statuses", StatusViewSet)
api.register(r"groups", GroupViewSet)
api.register(r"member-lists", MemberListViewSet)
api.register(r"events", EventViewSet)
api.register(r"event-types", EventTypeViewSet)
api.register(r"attachments", AttachmentViewSet)
api.register(r"emails", EmailMessageViewSet)


api.register(r"inventory/items", ItemViewSet)
api.register(r"inventory/categories", CategoryViewSet)
api.register(r"inventory/variants", ItemVariantViewSet)
api.register(r"inventory/locations", StorageLocationViewSet)
api.register(r"inventory/stocks", StockViewSet)
api.register(r"inventory/transactions", TransactionViewSet)


api.register(r"servicebook/services", ServiceViewSet)
api.register(r"servicebook/attendances", AttendanceViewSet)

# Orders endpoints
api.register(r"orders", OrderViewSet)
api.register(r"order-items", OrderItemViewSet)
api.register(r"orderable-items", OrderableItemViewSet)
api.register(r"order-statuses", OrderStatusViewSet)

# Qualifications endpoints - register most specific routes FIRST to avoid conflicts
# More specific routes must come before generic ones or they won't match
api.register(r"qualifications/types", QualificationTypeViewSet, basename="qualification-types")
api.register(r"qualifications/specialtask-types", SpecialTaskTypeViewSet, basename="qualification-specialtask-types")
api.register(r"qualifications/specialtasks", SpecialTaskViewSet, basename="qualification-specialtasks")
api.register(r"qualifications", QualificationViewSet, basename="qualifications")

# Settings endpoints
api.register(r"settings", SettingsViewSet, basename="settings")
api.register(r"settings/email-templates", EmailTemplateViewSet, basename="email-templates")
api.register(r"settings/email-layout-templates", EmailLayoutTemplateViewSet, basename="email-layout-templates")
api.register(r"ldap-department-mappings", LDAPDepartmentMappingViewSet, basename="ldap-department-mappings")
api.register(r"oidc-group-mappings", OIDCGroupMappingViewSet, basename="oidc-group-mappings")

# Training endpoints - most specific routes FIRST
api.register(r"training/library/categories", LibraryBlockCategoryViewSet, basename="training-library-categories")
api.register(r"training/library/tags", LibraryBlockTagViewSet, basename="training-library-tags")
api.register(r"training/library", LibraryBlockViewSet, basename="training-library")
api.register(r"training/sessions", TrainingSessionViewSet, basename="training-sessions")
api.register(r"training/blocks", TrainingBlockViewSet, basename="training-blocks")
