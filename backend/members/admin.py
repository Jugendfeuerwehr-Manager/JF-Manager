from django.contrib import admin

from .models import Attachment, Event, EventType, Group, Member, Parent, Status

# No import/export here: bulk exports of personal data run through the API,
# which scopes by department, asks for step-up and writes an ExportAudit.


class EventsInline(admin.TabularInline):
    model = Event
    autocomplete_fields = ["type", "member"]
    extra = 1


# Register your models here.
@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ["lastname", "name", "group", "status", "canSwimm", "birthday"]
    list_editable = ["group", "canSwimm", "status"]
    search_fields = ["name", "lastname"]
    ordering = ["lastname"]
    inlines = (EventsInline,)
    # autocomplete_fields = ['manager',]


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    ordering = ["lastname"]


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(EventType)
class EventTypeAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    ordering = ["name"]
    inlines = (EventsInline,)


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ["name", "content_type", "uploaded_by", "uploaded_at", "file_size"]
    list_filter = ["content_type", "uploaded_at", "mime_type"]
    search_fields = ["name", "description"]
    readonly_fields = ["uploaded_at", "file_size", "mime_type"]
    ordering = ["-uploaded_at"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("content_type", "uploaded_by")
