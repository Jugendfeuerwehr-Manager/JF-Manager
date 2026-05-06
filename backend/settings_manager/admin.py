from django.contrib import admin

from .models import LDAPConfig, LDAPDepartmentRoleMapping, SettingsCategory


@admin.register(SettingsCategory)
class SettingsCategoryAdmin(admin.ModelAdmin):
    """
    Admin-Interface für Einstellungskategorien
    """

    list_display = ("name", "code", "description")
    list_filter = ("code",)
    search_fields = ("name", "code", "description")
    readonly_fields = ("code",)  # Code sollte nicht geändert werden nach Erstellung

    fieldsets = ((None, {"fields": ("name", "code", "description")}),)

    def has_delete_permission(self, request, obj=None):
        # Verhindere Löschung von System-Kategorien
        if obj and obj.code in ["general", "email", "member", "service", "order", "ldap"]:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(LDAPConfig)
class LDAPConfigAdmin(admin.ModelAdmin):
    list_display = ("id", "enabled", "server_uri", "mirror_groups", "updated_at")
    readonly_fields = ("created_at", "updated_at")


@admin.register(LDAPDepartmentRoleMapping)
class LDAPDepartmentRoleMappingAdmin(admin.ModelAdmin):
    list_display = ("ldap_group_dn", "department", "revoke_on_mismatch")
    list_filter = ("department", "revoke_on_mismatch")
    search_fields = ("ldap_group_dn",)
    filter_horizontal = ("auth_groups",)
