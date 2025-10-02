from django.contrib import admin
from .models import SettingsCategory


@admin.register(SettingsCategory)
class SettingsCategoryAdmin(admin.ModelAdmin):
    """
    Admin-Interface für Einstellungskategorien
    """
    list_display = ('name', 'code', 'description')
    list_filter = ('code',)
    search_fields = ('name', 'code', 'description')
    readonly_fields = ('code',)  # Code sollte nicht geändert werden nach Erstellung
    
    fieldsets = (
        (None, {
            'fields': ('name', 'code', 'description')
        }),
    )
    
    def has_delete_permission(self, request, obj=None):
        # Verhindere Löschung von System-Kategorien
        if obj and obj.code in ['general', 'email', 'member', 'service', 'order']:
            return False
        return super().has_delete_permission(request, obj)
