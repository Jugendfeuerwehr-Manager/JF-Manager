"""Recording consents. Rows are only ever added, never changed."""

from django.contrib.auth import get_user_model

from members.models import Member, Parent
from privacy.models import ConsentRecord


def _subject_field(subject):
    if isinstance(subject, Member):
        return "member"
    if isinstance(subject, Parent):
        return "parent"
    if isinstance(subject, get_user_model()):
        return "user"
    raise TypeError(f"Unbekanntes Subjekt für eine Einwilligung: {type(subject).__name__}")


def record_consent(
    subject,
    kind,
    status,
    *,
    source,
    text_version="",
    text_snapshot="",
    recorded_by=None,
    note="",
):
    return ConsentRecord.objects.create(
        **{_subject_field(subject): subject},
        kind=kind,
        status=status,
        source=source,
        text_version=text_version,
        text_snapshot=text_snapshot,
        recorded_by=recorded_by,
        note=note,
    )


def history(subject):
    return ConsentRecord.objects.filter(**{_subject_field(subject): subject}).select_related("recorded_by")


def current_consents(subject):
    """Newest record per kind (``{kind: record}``)."""
    current = {}
    for record in history(subject):  # newest first
        current.setdefault(record.kind, record)
    return current


def has_consent(subject, kind):
    record = current_consents(subject).get(kind)
    return bool(record and record.status == ConsentRecord.Status.GRANTED)
