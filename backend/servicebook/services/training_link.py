"""Create a service together with its exercise in the training calendar."""

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from training.api.permissions import can_manage_training_department
from training.models import TrainingSession
from training.workflow import linked_service, sync_linked_service

FIELD = "create_training_session"


def _validate(user, data):
    department = data.get("department")
    if department is None:
        raise ValidationError(
            {FIELD: "Gemeinsame Dienste aller Abteilungen lassen sich nicht im Ausbildungskalender planen."}
        )
    if not can_manage_training_department(user, department.pk):
        raise PermissionDenied("Keine Berechtigung, im Ausbildungskalender dieser Abteilung zu planen.")
    if not (data.get("topic") or "").strip():
        raise ValidationError({"topic": "Für den Ausbildungskalender ist ein Thema nötig."})
    start = timezone.localtime(data["start"])
    end = timezone.localtime(data["end"])
    if start.date() != end.date():
        raise ValidationError({FIELD: "Ein Termin im Ausbildungskalender muss am selben Tag enden."})
    return start, end


@transaction.atomic
def create_service_with_training_session(user, data):
    """Publish an exercise for ``data`` and return the service it creates.

    The exercise owns the shared fields (time, topic, place, description,
    department), exactly as if it had been published in the training calendar;
    lead and events exist only on the service and are added afterwards.
    """
    start, end = _validate(user, data)
    session = TrainingSession.objects.create(
        status=TrainingSession.Status.PUBLISHED,
        title=data["topic"].strip(),
        description=data.get("description") or "",
        date=start.date(),
        start_time=start.time(),
        end_time=end.time(),
        location=data.get("place") or "",
        department=data["department"],
        created_by=user,
    )
    sync_linked_service(session)
    service = linked_service(session)
    if data.get("events"):
        service.events = data["events"]
        service.save(update_fields=["events"])
    service.operations_manager.set(data.get("operations_manager", []))
    return service
