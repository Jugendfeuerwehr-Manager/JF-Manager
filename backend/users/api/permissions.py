from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminUser(BasePermission):
    """Superusers manage identities and privileges; staff has read-only access."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return request.user.is_staff and request.method in SAFE_METHODS


class IdentityModelPermissions(BasePermission):
    """Global model permissions, without a staff bypass or scoped identity rights."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        model = view.queryset.model if getattr(view, "queryset", None) is not None else None
        if model is None:
            from django.contrib.auth.models import Permission

            model = Permission
        verb = {
            "list": "view",
            "retrieve": "view",
            "create": "add",
            "partial_update": "change",
            "update": "change",
            "set_groups": "change",
            "destroy": "delete",
        }.get(view.action)
        # User deletion is a deactivation, not removal of personal records.
        if view.action == "destroy" and model._meta.label_lower == "users.customuser":
            verb = "change"
        if verb is None:
            return False
        required = f"{model._meta.app_label}.{verb}_{model._meta.model_name}"
        if model._meta.label_lower == "auth.permission":
            return user.has_perm("auth.view_group")
        if view.action == "set_groups":
            return user.has_perm(required) and user.has_perm("departments.can_assign_roles")
        if model._meta.label_lower == "departments.userdepartmentrole" and request.method not in SAFE_METHODS:
            return user.has_perm(required) and user.has_perm("departments.can_assign_roles")
        return user.has_perm(required)
