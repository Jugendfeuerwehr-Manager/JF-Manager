"""Recording the committee's resolution on applications."""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from admissions.models import AdmissionDecision, Application, Seal
from admissions.services import seal as seal_service
from admissions.services.submission import SUBJECT

STATUS_FOR_OUTCOME = {
    AdmissionDecision.Outcome.APPROVED: Application.Status.APPROVED,
    AdmissionDecision.Outcome.REJECTED: Application.Status.REJECTED,
    AdmissionDecision.Outcome.DEFERRED: Application.Status.DEFERRED,
}


def decision_content(decision):
    """What the decision seal covers."""
    meeting = decision.meeting
    return {
        "application": decision.application_id,
        "body": decision.body,
        "decided_on": decision.decided_on.isoformat(),
        "outcome": decision.outcome,
        "votes": [decision.votes_yes, decision.votes_no, decision.votes_abstain],
        "note": decision.note,
        "meeting": {"id": meeting.pk, "date": meeting.date.isoformat(), "protocol": meeting.protocol_ref}
        if meeting
        else None,
        "recorded_by": decision.recorded_by_id,
        "recorded_at": decision.recorded_at.isoformat(),
    }


def record_decision(
    application, *, outcome, decided_on, meeting=None, body="", votes=(None, None, None), note="", by=None
):
    """Store and seal a resolution and move the application on. Only open applications can be decided."""
    if outcome not in STATUS_FOR_OUTCOME:
        raise ValidationError({"outcome": "Unbekanntes Ergebnis."})
    if meeting is not None and meeting.department_id != application.department_id:
        raise ValidationError({"meeting": "Die Sitzung gehört zu einer anderen Abteilung."})
    if decided_on < application.submitted_at.date():
        raise ValidationError({"decided_on": "Der Beschluss kann nicht vor dem Antrag liegen."})

    with transaction.atomic():
        application = Application.objects.select_for_update().get(pk=application.pk)
        if application.status not in Application.OPEN_STATUSES:
            raise ValidationError(
                {"detail": f"Über diesen Antrag ist bereits entschieden ({application.get_status_display()})."}
            )
        votes_yes, votes_no, votes_abstain = votes
        decision = AdmissionDecision.objects.create(
            application=application,
            meeting=meeting,
            body=body or (meeting.body if meeting else application.form_version.form.decision_body),
            decided_on=meeting.date if meeting else decided_on,
            outcome=outcome,
            votes_yes=votes_yes,
            votes_no=votes_no,
            votes_abstain=votes_abstain,
            note=note,
            recorded_by=by,
        )
        application.status = STATUS_FOR_OUTCOME[outcome]
        application.save(update_fields=["status"])
        seal_service.seal(
            subject_type=SUBJECT, subject_id=application.pk, kind=Seal.Kind.DECISION, content=decision_content(decision)
        )
    _close_task(application, by)
    return decision


def _close_task(application, by):
    from notifications import inbox

    inbox.complete_tasks(application, kind="admission_submitted", by=by)
