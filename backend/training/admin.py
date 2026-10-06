from django.contrib import admin
from django.db import transaction

from training.admin_forms import VersionedBlockForm, VersionedSessionForm
from training.api.plan import advance_revision, delete_plan_blocks, lock_sessions
from training.models import (
    LibraryBlock,
    LibraryBlockCategory,
    LibraryBlockTag,
    TrainingBlock,
    TrainingMedia,
    TrainingSession,
)
from training.workflow import requires_service_confirmation, sync_linked_service


@admin.register(LibraryBlockCategory)
class LibraryBlockCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "color", "icon"]
    search_fields = ["name"]


@admin.register(LibraryBlockTag)
class LibraryBlockTagAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


@admin.register(LibraryBlock)
class LibraryBlockAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "default_duration_minutes", "is_public", "created_by", "created_at"]
    list_filter = ["category", "is_public", "tags"]
    search_fields = ["title", "description"]
    readonly_fields = ["export_uuid", "created_at", "updated_at"]
    filter_horizontal = ["tags"]


@admin.register(TrainingSession)
class TrainingSessionAdmin(admin.ModelAdmin):
    form = VersionedSessionForm
    list_display = ["title", "status", "revision", "date", "start_time", "end_time", "location", "created_by"]
    list_filter = ["status", "date", "groups"]
    search_fields = ["title", "location"]
    readonly_fields = ["created_at", "updated_at"]
    filter_horizontal = ["groups"]
    date_hierarchy = "date"

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change:
            advance_revision(obj)
        sync_linked_service(obj)


@admin.register(TrainingBlock)
class TrainingBlockAdmin(admin.ModelAdmin):
    form = VersionedBlockForm
    list_display = ["title", "session", "duration_minutes", "start_offset_minutes", "library_block"]
    list_filter = ["session", "groups"]
    search_fields = ["title"]
    readonly_fields = ["created_at", "updated_at"]
    filter_horizontal = ["groups"]

    def save_model(self, request, obj, form, change):
        old = TrainingBlock.objects.filter(pk=obj.pk).values_list("session_id", flat=True).first()
        parents = lock_sessions([old, obj.session_id])
        super().save_model(request, obj, form, change)
        for parent in parents:
            advance_revision(parent)

    def has_delete_permission(self, request, obj=None):
        # Documented plans are removed through the explicitly confirmed plan editor.
        if obj is not None and requires_service_confirmation(obj.session):
            return False
        return super().has_delete_permission(request, obj)

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

    def delete_model(self, request, obj):
        with transaction.atomic():
            parent = lock_sessions([obj.session_id])[0]
            delete_plan_blocks(TrainingBlock.objects.filter(pk=obj.pk))
            advance_revision(parent)


@admin.register(TrainingMedia)
class TrainingMediaAdmin(admin.ModelAdmin):
    list_display = ["original_filename", "content_type", "object_id", "uploaded_by", "created_at"]
    readonly_fields = ["created_at"]
