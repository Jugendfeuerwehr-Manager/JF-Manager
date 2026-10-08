from django.contrib import admin

from .models import AccountLink


@admin.register(AccountLink)
class AccountLinkAdmin(admin.ModelAdmin):
    """Read only: links are created by invitations and the checked staff workflow."""

    list_display = ["user", "parent", "member", "status", "linked_at", "confirmed_at"]
    list_filter = ["status"]
    search_fields = ["user__username", "user__email"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
