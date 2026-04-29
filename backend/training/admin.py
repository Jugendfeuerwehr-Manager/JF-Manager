from django.contrib import admin

from training.models import (
    LibraryBlock,
    LibraryBlockCategory,
    LibraryBlockTag,
    TrainingBlock,
    TrainingMedia,
    TrainingSession,
)


@admin.register(LibraryBlockCategory)
class LibraryBlockCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'icon']
    search_fields = ['name']


@admin.register(LibraryBlockTag)
class LibraryBlockTagAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(LibraryBlock)
class LibraryBlockAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'default_duration_minutes', 'is_public', 'created_by', 'created_at']
    list_filter = ['category', 'is_public', 'tags']
    search_fields = ['title', 'description']
    readonly_fields = ['export_uuid', 'created_at', 'updated_at']
    filter_horizontal = ['tags']


@admin.register(TrainingSession)
class TrainingSessionAdmin(admin.ModelAdmin):
    list_display = ['title', 'date', 'start_time', 'end_time', 'location', 'created_by']
    list_filter = ['date', 'groups']
    search_fields = ['title', 'location']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['groups']
    date_hierarchy = 'date'


@admin.register(TrainingBlock)
class TrainingBlockAdmin(admin.ModelAdmin):
    list_display = ['title', 'session', 'duration_minutes', 'start_offset_minutes', 'library_block']
    list_filter = ['session', 'groups']
    search_fields = ['title']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['groups']


@admin.register(TrainingMedia)
class TrainingMediaAdmin(admin.ModelAdmin):
    list_display = ['original_filename', 'content_type', 'object_id', 'uploaded_by', 'created_at']
    readonly_fields = ['created_at']
