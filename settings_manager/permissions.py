from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from functools import wraps


def require_settings_permission(permission_name):
    """
    Decorator für View-Funktionen, die spezielle Einstellungsberechtigungen benötigen
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.has_perm(f'settings_manager.{permission_name}'):
                raise PermissionDenied(f"Sie haben keine Berechtigung für: {permission_name}")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


class SettingsPermissionMixin(PermissionRequiredMixin):
    """
    Mixin für Class-Based Views mit Einstellungsberechtigungen
    """
    
    def get_permission_required(self):
        """
        Überschreibt die Standard-Permission-Logik für Einstellungen
        """
        if hasattr(self, 'settings_permission'):
            return f'settings_manager.{self.settings_permission}'
        return super().get_permission_required()
    
    def handle_no_permission(self):
        """
        Custom handling für fehlende Berechtigungen
        """
        raise PermissionDenied(
            "Sie haben keine Berechtigung, diese Einstellungen zu verwalten. "
            "Wenden Sie sich an Ihren Administrator."
        )


class CategoryPermissionMixin:
    """
    Mixin um automatisch Kategorien-basierte Berechtigungen zu handhaben
    """
    
    def get_category_permissions(self, category_code):
        """
        Gibt die erforderlichen Berechtigungen für eine Kategorie zurück
        """
        return {
            'view': f'view_{category_code}_settings',
            'change': f'change_{category_code}_settings'
        }
    
    def check_category_permission(self, user, category_code, permission_type='view'):
        """
        Prüft ob der User Berechtigung für eine Kategorie hat
        """
        # Superuser hat alle Berechtigungen
        if user.is_superuser:
            return True
            
        # Prüfe spezifische Berechtigung
        permission = f'settings_manager.{permission_type}_{category_code}_settings'
        if user.has_perm(permission):
            return True
            
        # Prüfe globale Berechtigung
        global_permission = f'settings_manager.{permission_type}_all_settings'
        if user.has_perm(global_permission):
            return True
            
        return False