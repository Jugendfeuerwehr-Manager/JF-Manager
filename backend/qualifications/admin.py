from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import QualificationType, Qualification, SpecialTaskType, SpecialTask


class QualificationTypeResource(resources.ModelResource):
    class Meta:
        model = QualificationType
        skip_unchanged = True


class QualificationResource(resources.ModelResource):
    class Meta:
        model = Qualification
        skip_unchanged = True


class SpecialTaskTypeResource(resources.ModelResource):
    class Meta:
        model = SpecialTaskType
        skip_unchanged = True


class SpecialTaskResource(resources.ModelResource):
    class Meta:
        model = SpecialTask
        skip_unchanged = True


@admin.register(QualificationType)
class QualificationTypeAdmin(ImportExportModelAdmin):
    resource_class = QualificationTypeResource
    list_display = ['name', 'expires', 'validity_period', 'description']
    list_filter = ['expires']
    search_fields = ['name', 'description']
    ordering = ['name']


@admin.register(Qualification)
class QualificationAdmin(ImportExportModelAdmin):
    resource_class = QualificationResource
    list_display = ['get_person_name', 'type', 'date_acquired', 'date_expires', 'is_expired', 'issued_by']
    list_filter = ['type', 'date_acquired', 'date_expires']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 
                    'member__name', 'member__lastname', 'type__name', 'issued_by']
    ordering = ['-date_acquired']
    autocomplete_fields = ['user', 'member', 'type']
    
    def get_person_name(self, obj):
        return obj.get_person_name()
    get_person_name.short_description = 'Person'

    def is_expired(self, obj):
        return obj.is_expired()
    is_expired.boolean = True
    is_expired.short_description = 'Abgelaufen'


@admin.register(SpecialTaskType)
class SpecialTaskTypeAdmin(ImportExportModelAdmin):
    resource_class = SpecialTaskTypeResource
    list_display = ['name', 'description']
    search_fields = ['name', 'description']
    ordering = ['name']


@admin.register(SpecialTask)
class SpecialTaskAdmin(ImportExportModelAdmin):
    resource_class = SpecialTaskResource
    list_display = ['get_person_name', 'task', 'start_date', 'end_date', 'is_active']
    list_filter = ['task', 'start_date', 'end_date']
    search_fields = ['user__username', 'user__first_name', 'user__last_name',
                    'member__name', 'member__lastname', 'task__name']
    ordering = ['-start_date']
    autocomplete_fields = ['user', 'member', 'task']
    
    def get_person_name(self, obj):
        return obj.get_person_name()
    get_person_name.short_description = 'Person'

    def is_active(self, obj):
        return obj.is_active()
    is_active.boolean = True
    is_active.short_description = 'Aktiv'
