"""
Custom permissions for Settings API
"""

from rest_framework import permissions


class CanViewSettings(permissions.BasePermission):
    """
    Permission to view all settings
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False

        # Superusers can always view
        if request.user.is_superuser:
            return True

        # Check for global view permission
        return request.user.has_perm('settings_manager.view_all_settings')


class CanChangeSettings(permissions.BasePermission):
    """
    Permission to change all settings
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False

        # Read operations allowed for users with view permission
        if request.method in permissions.SAFE_METHODS:
            return CanViewSettings().has_permission(request, view)

        # Write operations require change permission
        if request.user.is_superuser:
            return True

        return request.user.has_perm('settings_manager.change_all_settings')


class CanViewCategorySettings(permissions.BasePermission):
    """
    Permission to view specific category settings
    Checks permissions based on the category in the request
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False

        # Superusers can always view
        if request.user.is_superuser:
            return True

        # Get category from view action or query params
        category = None
        if hasattr(view, 'action') and view.action in ['general', 'email', 'member', 'service', 'order']:
                category = view.action

        if not category:
            category = request.query_params.get('category')

        if not category:
            # If no specific category, check global permission
            return request.user.has_perm('settings_manager.view_all_settings')

        # Check category-specific permission
        permission = f'settings_manager.view_{category}_settings'
        return (
            request.user.has_perm(permission) or
            request.user.has_perm('settings_manager.view_all_settings')
        )


class CanChangeCategorySettings(permissions.BasePermission):
    """
    Permission to change specific category settings
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False

        # Read operations allowed for users with view permission
        if request.method in permissions.SAFE_METHODS:
            return CanViewCategorySettings().has_permission(request, view)

        # Superusers can always change
        if request.user.is_superuser:
            return True

        # Get category from view action or request data
        category = None
        if hasattr(view, 'action') and view.action in ['general', 'email', 'member', 'service', 'order']:
            category = view.action

        if not category and request.method in ['POST', 'PUT', 'PATCH']:
            category = request.data.get('category')

        if not category:
            # If no specific category, check global permission
            return request.user.has_perm('settings_manager.change_all_settings')

        # Check category-specific permission
        permission = f'settings_manager.change_{category}_settings'
        return (
            request.user.has_perm(permission) or
            request.user.has_perm('settings_manager.change_all_settings')
        )
