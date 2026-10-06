"""
Custom permissions for Orders API
"""

from rest_framework import permissions

from jf_manager_backend.permissions import DepartmentRoleModelPermissions


class CanManageOrders(DepartmentRoleModelPermissions):
    """
    Permission to manage orders (create, update, delete)
    """

    def _required_permissions(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return []
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            return ["orders.can_manage_orders"]
        return None


class CanChangeOrderStatus(permissions.BasePermission):
    """
    Permission to change order status
    """

    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            # Check if action is related to status change
            if view.action in ["update_status", "bulk_update_status"]:
                return request.user.has_perm("orders.can_change_order_status")
            return True
        return False


class IsOrderOwnerOrStaff(permissions.BasePermission):
    """
    Permission to allow order owner or staff to access
    """

    def has_object_permission(self, request, view, obj):
        # Staff can do anything
        if request.user and request.user.is_staff:
            return True

        # Order owner can read
        if request.method in permissions.SAFE_METHODS:
            # Check if user is the one who ordered or is related to the member
            return obj.ordered_by == request.user or obj.member.user == request.user

        # Write operations require staff or manage_orders permission
        return request.user and request.user.has_perm("orders.can_manage_orders")
