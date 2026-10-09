from rest_framework.permissions import BasePermission

from .access import FORBIDDEN_DETAIL, is_portal_account, portal_route_allowed


class StaffAccountRequired(BasePermission):
    """Second layer behind PortalBoundaryMiddleware in the DRF defaults."""

    message = FORBIDDEN_DETAIL

    def has_permission(self, request, view):
        if not is_portal_account(request.user):
            return True
        return getattr(view, "portal_access", False) is True or portal_route_allowed(
            getattr(request._request, "resolver_match", None)
        )


class PortalAccountRequired(BasePermission):
    """Portal endpoints: only signed-in portal accounts. Object binding stays with the view."""

    def has_permission(self, request, view):
        return is_portal_account(request.user)
