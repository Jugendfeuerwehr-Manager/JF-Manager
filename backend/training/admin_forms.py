"""Admin writers participate in the same plan version and time contract."""

from django import forms
from rest_framework.exceptions import ValidationError as APIValidationError

from training.api.plan import lock_sessions
from training.api.validation import validate_block_times, validate_session_times
from training.models import TrainingBlock, TrainingSession
from training.workflow import validate_documented_change, validate_workflow


def as_form_error(error):
    def messages(detail):
        if isinstance(detail, dict):
            return [text for value in detail.values() for text in messages(value)]
        if isinstance(detail, (list, tuple)):
            return [text for value in detail for text in messages(value)]
        return [str(detail)]

    return forms.ValidationError(messages(error.detail))


class VersionedSessionForm(forms.ModelForm):
    expected_revision = forms.IntegerField(widget=forms.HiddenInput, required=False)
    confirm_service_change = forms.BooleanField(
        required=False, label="Änderung am begonnenen/dokumentierten Dienst ausdrücklich bestätigen"
    )

    class Meta:
        model = TrainingSession
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["expected_revision"].initial = self.instance.revision

    def clean(self):
        data = super().clean()
        locked = lock_sessions([self.instance.pk]) if self.instance.pk else []
        current = locked[0] if locked else None
        if current and data.get("expected_revision") != current.revision:
            raise forms.ValidationError(
                "Der Plan wurde inzwischen geändert. Formular neu laden; Eingaben vorher sichern."
            )
        try:
            if data.get("start_time") and data.get("end_time"):
                frame = validate_session_times(data["start_time"], data["end_time"])
                if current:
                    for block in current.blocks.all():
                        validate_block_times(block.start_offset_minutes, block.duration_minutes, frame)
            validate_workflow(current, data, data.get("confirm_service_change", False))
        except APIValidationError as exc:
            raise as_form_error(exc) from exc
        department = data.get("department")
        if current and any(
            group.department_id != getattr(department, "pk", None)
            for block in current.blocks.all()
            for group in block.groups.all()
        ):
            raise forms.ValidationError(
                "Bausteingruppen müssen zur Trainingsabteilung gehören; Zuordnungen zuerst im Planer ändern."
            )
        if any(group.department_id != getattr(department, "pk", None) for group in data.get("groups", [])):
            raise forms.ValidationError("Gruppen müssen zur Trainingsabteilung gehören.")
        return data


class VersionedBlockForm(forms.ModelForm):
    expected_revision = forms.IntegerField(widget=forms.HiddenInput, required=False)
    confirm_service_change = forms.BooleanField(
        required=False, label="Änderung am begonnenen/dokumentierten Dienst ausdrücklich bestätigen"
    )

    class Meta:
        model = TrainingBlock
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["expected_revision"].initial = self.instance.session.revision

    def clean(self):
        data = super().clean()
        session = data.get("session")
        if session is None:
            return data
        # Lock old and new parents in the same order as the API.
        old_session_id = TrainingBlock.objects.filter(pk=self.instance.pk).values_list("session_id", flat=True).first()
        locked = {item.pk: item for item in lock_sessions([session.pk, old_session_id])}
        if old_session_id and data.get("expected_revision") != locked[old_session_id].revision:
            raise forms.ValidationError(
                "Der Plan wurde inzwischen geändert. Formular neu laden; Eingaben vorher sichern."
            )
        session = locked[session.pk]
        try:
            for parent in locked.values():
                validate_documented_change(parent, data.get("confirm_service_change", False))
            if data.get("start_offset_minutes") is not None and data.get("duration_minutes") is not None:
                frame = validate_session_times(session.start_time, session.end_time)
                validate_block_times(data["start_offset_minutes"], data["duration_minutes"], frame)
        except APIValidationError as exc:
            raise as_form_error(exc) from exc
        if any(group.department_id != session.department_id for group in data.get("groups", [])):
            raise forms.ValidationError("Gruppen müssen zur Trainingsabteilung gehören.")
        return data
