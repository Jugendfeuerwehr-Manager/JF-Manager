from django import forms
from django.contrib import admin

from .hierarchy import find_cycle
from .models import Qualification, QualificationType, SpecialTask, SpecialTaskType


class QualificationTypeAdminForm(forms.ModelForm):
    class Meta:
        model = QualificationType
        fields = "__all__"

    def clean_includes(self):
        included = self.cleaned_data["includes"]
        own_id = self.instance.pk
        if own_id is not None and find_cycle(own_id, [t.pk for t in included]):
            raise forms.ValidationError(
                "Eine Qualifikation kann sich weder selbst noch (über Zwischenstufen) zyklisch einschließen."
            )
        return included


@admin.register(QualificationType)
class QualificationTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "expires", "validity_period", "description"]
    list_filter = ["expires"]
    search_fields = ["name", "description"]
    ordering = ["name"]
    filter_horizontal = ["includes"]
    form = QualificationTypeAdminForm


@admin.register(Qualification)
class QualificationAdmin(admin.ModelAdmin):
    list_display = ["get_person_name", "type", "date_acquired", "date_expires", "is_expired", "issued_by"]
    list_filter = ["type", "date_acquired", "date_expires"]
    search_fields = [
        "user__username",
        "user__first_name",
        "user__last_name",
        "member__name",
        "member__lastname",
        "type__name",
        "issued_by",
    ]
    ordering = ["-date_acquired"]
    autocomplete_fields = ["user", "member", "type"]

    def get_person_name(self, obj):
        return obj.get_person_name()

    get_person_name.short_description = "Person"

    def is_expired(self, obj):
        return obj.is_expired()

    is_expired.boolean = True
    is_expired.short_description = "Abgelaufen"


@admin.register(SpecialTaskType)
class SpecialTaskTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "description"]
    search_fields = ["name", "description"]
    ordering = ["name"]


@admin.register(SpecialTask)
class SpecialTaskAdmin(admin.ModelAdmin):
    list_display = ["get_person_name", "task", "start_date", "end_date", "is_active"]
    list_filter = ["task", "start_date", "end_date"]
    search_fields = [
        "user__username",
        "user__first_name",
        "user__last_name",
        "member__name",
        "member__lastname",
        "task__name",
    ]
    ordering = ["-start_date"]
    autocomplete_fields = ["user", "member", "task"]

    def get_person_name(self, obj):
        return obj.get_person_name()

    get_person_name.short_description = "Person"

    def is_active(self, obj):
        return obj.is_active()

    is_active.boolean = True
    is_active.short_description = "Aktiv"
