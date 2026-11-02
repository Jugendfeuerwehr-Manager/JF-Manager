"""Recording consents. Rows are only ever added, never changed."""

from django.contrib.auth import get_user_model
from django.db import transaction

from members.models import Member, Parent
from privacy.models import ConsentKind, ConsentRecord


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


def kind_labels():
    """``{slug: label}`` for all kinds, also inactive ones (old records keep their name)."""
    return dict(ConsentKind.objects.values_list("slug", "label"))


def portal_kinds():
    return ConsentKind.objects.filter(active=True, in_portal=True)


def change_from_portal(member, kind, status, *, user):
    """A parent grants or withdraws a consent for a child in the portal.

    Withdrawing is a new row as well; the wording and its version are stored with
    it. The responsible youth directors hear about it once the row is committed.
    """
    record = record_consent(
        member,
        kind.slug,
        status,
        source=ConsentRecord.Source.SELF,
        text_version=kind.text_version,
        text_snapshot=kind.description or kind.label,
        recorded_by=user,
        note="Im Portal erklärt",
    )

    def notify():
        from notifications.consent_producers import consent_changed

        consent_changed(record.pk)

    transaction.on_commit(notify)
    return record


def save_kind(kind, data):
    """Create or update a kind; a changed wording raises its version."""
    if kind.pk and "description" in data and data["description"] != kind.description:
        kind.version += 1
    for field, value in data.items():
        setattr(kind, field, value)
    kind.save()
    return kind


def delete_kind(kind):
    """Only unused, self-made kinds disappear; everything else is deactivated instead."""
    if kind.built_in or ConsentRecord.objects.filter(kind=kind.slug).exists():
        return False
    kind.delete()
    return True
