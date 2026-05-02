from django.contrib import admin

from .models import Department, UserDepartmentRole


class UserDepartmentRoleInline(admin.TabularInline):
    model = UserDepartmentRole
    extra = 0
    autocomplete_fields = ["user"]


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "phone", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "code"]
    prepopulated_fields = {"code": ("name",)}
    inlines = [UserDepartmentRoleInline]


@admin.register(UserDepartmentRole)
class UserDepartmentRoleAdmin(admin.ModelAdmin):
    list_display = ["user", "department"]
    list_filter = ["department"]
    autocomplete_fields = ["user"]
    filter_horizontal = ["groups"]
