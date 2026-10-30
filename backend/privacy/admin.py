from django.contrib import admin

from .models import ConsentRecord, LegalPage, LegalPageVersion


@admin.register(LegalPage)
class LegalPageAdmin(admin.ModelAdmin):
    list_display = ["kind", "draft_title", "updated_at"]
    readonly_fields = ["updated_at", "updated_by"]


@admin.register(LegalPageVersion)
class LegalPageVersionAdmin(admin.ModelAdmin):
    # Published versions are evidence for consents: read-only.
    list_display = ["page", "version", "title", "published_at"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    list_display = ["kind", "status", "member", "parent", "user", "source", "recorded_at"]
    list_filter = ["kind", "status", "source"]

    def has_change_permission(self, request, obj=None):
        return False
