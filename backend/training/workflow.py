"""Stable service identity and explicit changes to documented exercises."""

from datetime import datetime

from django.utils import timezone
from rest_framework import serializers

from servicebook.models import Service
from training.models import TrainingSession


def linked_service(session, *, lock=False):
    if not session.pk:
        return None
    queryset = Service.objects.filter(training_session_id=session.pk)
    if lock:
        queryset = queryset.select_for_update()
    return queryset.first()


def service_is_documented(service):
    return bool(
        service
        and (
            service.start <= timezone.now()
            or service.events
            or service.attendance_set.exists()
            or service.staff_attendances.exists()
        )
    )


def requires_service_confirmation(session):
    return service_is_documented(linked_service(session))


def validate_documented_change(session, confirmed):
    if service_is_documented(linked_service(session, lock=True)) and not confirmed:
        raise serializers.ValidationError(
            {
                "confirm_service_change": "Der Dienst hat begonnen oder enthält Dokumentation. Änderung ausdrücklich bestätigen; Anwesenheiten bleiben erhalten."
            }
        )


def validate_workflow(session, attrs, confirmed=False):
    target = attrs.get("status", getattr(session, "status", TrainingSession.Status.DRAFT))
    service = linked_service(session, lock=True) if session else None
    if service and target == TrainingSession.Status.DRAFT:
        raise serializers.ValidationError(
            {"status": "Eine verknüpfte Übung kann nicht zum Entwurf zurückkehren. Bei Bedarf absagen."}
        )
    if target == TrainingSession.Status.COMPLETED and not service:
        raise serializers.ValidationError({"status": "Die Übung muss vor dem Abschluss veröffentlicht werden."})
    if service_is_documented(service):
        department = attrs.get("department", session.department)
        if getattr(department, "pk", None) != service.department_id:
            raise serializers.ValidationError(
                {"department": "Die Abteilung eines dokumentierten Dienstes kann nicht geändert werden."}
            )
        validate_documented_change(session, confirmed)


def sync_linked_service(session):
    service = linked_service(session, lock=True)
    if session.status != TrainingSession.Status.PUBLISHED and not service:
        return
    # Completed/cancelled retain the original service and all documentation.
    if session.status != TrainingSession.Status.PUBLISHED:
        return
    values = {
        "start": timezone.make_aware(datetime.combine(session.date, session.start_time)),
        "end": timezone.make_aware(datetime.combine(session.date, session.end_time)),
        "topic": session.title,
        "place": session.location,
        "description": session.description,
        "department": session.department,
    }
    if service is None:
        Service.objects.create(training_session=session, **values)
    else:
        for key, value in values.items():
            setattr(service, key, value)
        service.save(update_fields=list(values))
