from rest_framework.permissions import SAFE_METHODS, BasePermission


def has_privacy_settings_right(user, operation):
    """Same model as the other settings categories (settings_manager.*_settings)."""
    if not (user and user.is_authenticated):
        return False
    return (
        user.is_superuser
        or user.has_perm(f"settings_manager.{operation}_privacy_settings")
        or user.has_perm(f"settings_manager.{operation}_all_settings")
    )


class PrivacySettingsPermission(BasePermission):
    """Legal texts are organisation configuration, so they follow the settings rights
    instead of model rights (CustomDefaultPermissions does not fit central records)."""

    def has_permission(self, request, view):
        return has_privacy_settings_right(request.user, "view" if request.method in SAFE_METHODS else "change")
