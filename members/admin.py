from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from .models import Member, Parent, EventType, Event, Group, Status
from import_export import resources


class MemberRessource(resources.ModelResource):

    class Meta:
        model = Member
        skip_unchanged = True


class EventsInline(admin.TabularInline):
    model = Event
    autocomplete_fields = ['type', 'member']
    extra = 1



# Register your models here.
@admin.register(Member)
class MemberAdmin(ImportExportModelAdmin):
    list_display = ['lastname', 'name', 'group', 'status', 'canSwimm', 'birthday']
    list_editable = ['group', 'canSwimm', 'status']
    search_fields = ['name', 'lastname']
    ordering = ['lastname']
    inlines = (EventsInline,)
    #autocomplete_fields = ['manager',]


@admin.register(Parent)
class ParentAdmin(ImportExportModelAdmin):
    search_fields = ['name']
    ordering = ['lastname']


@admin.register(Group)
class GroupAdmin(ImportExportModelAdmin):
    search_fields = ['name']

@admin.register(Status)
class GroupAdmin(ImportExportModelAdmin):
    search_fields = ['name']

@admin.register(EventType)
class ParentAdmin(ImportExportModelAdmin):
    search_fields = ['name']
    ordering = ['name']
    inlines = (EventsInline,)