"""Taking an approved application over into the member administration."""

from datetime import date

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from admissions.field_catalog import EXTRA_PREFIX, MEMBER_CATALOG
from admissions.models import Application, ApplicationFile
from admissions.schema import iter_elements
from members.models import Member, Parent
from membership.services import lifecycle
from privacy.models import ConsentRecord
from privacy.services.consent import record_consent

LEGAL_CONSENT_KINDS = {"privacy": "privacy_notice_ack", "portal_terms": "portal_terms_ack"}
GUARDIAN_FIELDS = ("name", "lastname", "street", "zip_code", "city", "phone", "mobile", "email", "email2")


def _elements(application):
    return [element for _, element in iter_elements(application.form_version.schema) if element.get("key")]


def guardian_rows(application):
    for element in _elements(application):
        if element["type"] == "guardians":
            return application.answers.get(element["key"]) or []
    return []


def parent_suggestions(application):
    """Existing parents of the department with a matching e-mail, per guardian row (for the review UI)."""
    suggestions = []
    for row in guardian_rows(application):
        emails = [email for email in (row.get("email"), row.get("email2")) if email]
        if not emails:
            suggestions.append([])
            continue
        matches = (
            Parent.objects.filter(children__departments=application.department_id)
            .filter(Q(email__in=emails) | Q(email2__in=emails))
            .distinct()
        )
        suggestions.append(
            [{"id": parent.pk, "name": parent.get_full_name(), "email": parent.email} for parent in matches]
        )
    return suggestions


def _member_values(application):
    values = {}
    for element in _elements(application):
        target = element.get("target")
        field = MEMBER_CATALOG.get(target)
        if field is None or field.key == "member.avatar":
            continue
        value = application.answers.get(element["key"])
        if value in (None, ""):
            continue
        if field.model_field == "birthday":
            value = date.fromisoformat(value)
        values[field.model_field] = value
    return values


def _extra_values(application):
    """Answers for additional member fields, cleaned like a member dialog write.

    A field deactivated or removed since the application stays in the sealed application only.
    """
    from members.services.extra_fields import clean_values, definitions_for

    raw = {}
    for element in _elements(application):
        target = element.get("target") or ""
        if not target.startswith(EXTRA_PREFIX):
            continue
        value = application.answers.get(element["key"])
        if value not in (None, ""):
            raw[target.removeprefix(EXTRA_PREFIX)] = value
    definitions = list(definitions_for([application.department_id]))
    known = {definition.key for definition in definitions}
    merged, _ = clean_values({key: value for key, value in raw.items() if key in known}, definitions)
    return merged


def _consents(application, member, parents, by):
    for element in _elements(application):
        if application.answers.get(element["key"]) is not True:
            continue
        if element["type"] == "consent":
            frozen = element.get("consent") or {}
            subjects = parents if element.get("person") == "guardians" else [member]
            kind = element["consent_kind"]
        elif element["type"] == "legal_ack" and element.get("legal_kind") in LEGAL_CONSENT_KINDS:
            frozen = {"version": element["legal"]["version"], "text": element["legal"]["title"]}
            subjects = [member, *parents]
            kind = LEGAL_CONSENT_KINDS[element["legal_kind"]]
        else:
            continue
        for subject in subjects:
            record_consent(
                subject,
                kind,
                ConsentRecord.Status.GRANTED,
                source=ConsentRecord.Source.APPLICATION,
                text_version=str(frozen.get("version", "")),
                text_snapshot=frozen.get("text", ""),
                recorded_by=by,
                note=f"Aufnahmeantrag #{application.pk} vom {application.submitted_at:%d.%m.%Y}",
            )


def take_over(application, *, joined=None, parent_links=None, invite_parents=False, by=None):
    """Create the member and the guardians from an approved application.

    ``parent_links`` maps a guardian row (index) to an existing parent id the reviewer chose;
    rows without a link become new parents.
    """
    parent_links = {int(index): parent_id for index, parent_id in (parent_links or {}).items() if parent_id}
    with transaction.atomic():
        application = (
            Application.objects.select_for_update().select_related("form_version__form").get(pk=application.pk)
        )
        if application.status != Application.Status.APPROVED:
            raise ValidationError({"detail": "Nur angenommene Anträge können übernommen werden."})
        decision = application.decisions.order_by("-recorded_at").first()
        joined = joined or (decision.decided_on if decision else timezone.localdate())

        form = application.form_version.form
        member = Member.objects.create(
            **_member_values(application),
            extra_fields=_extra_values(application),
            joined=joined,
            status=form.initial_status,
        )
        member.departments.add(application.department_id)
        photo = application.files.filter(kind=ApplicationFile.Kind.PHOTO).first()
        if photo:
            member.avatar.save(f"member-{member.pk}.jpg", photo.file.open("rb"), save=True)
            photo.file.close()

        parents = []
        for index, row in enumerate(guardian_rows(application)):
            parent = _link_or_create_parent(application, row, parent_links.get(index))
            parent.children.add(member)
            parents.append(parent)

        _attachments(application, member, by)
        lifecycle.admit(member, on=joined, by=by, note=f"Aufnahmeantrag #{application.pk}")
        _consents(application, member, parents, by)

        application.member = member
        application.status = Application.Status.TAKEN_OVER
        application.taken_over_at = timezone.now()
        application.taken_over_by = by
        application.save(update_fields=["member", "status", "taken_over_at", "taken_over_by"])
        if invite_parents and by is not None:
            transaction.on_commit(lambda: _invite(parents, by))
    return member


def _attachments(application, member, by):
    """PDFs from the application become attachments of the member (the sealed copies stay)."""
    from django.core.files.base import ContentFile

    from members.models import Attachment

    labels = {element["key"]: element.get("label") or "Anlage" for element in _elements(application)}
    for item in application.files.filter(kind=ApplicationFile.Kind.ATTACHMENT).order_by("key"):
        answer = application.answers.get(item.key) or {}
        with item.file.open("rb") as source:
            content = ContentFile(source.read(), name=f"{item.key}.pdf")
        Attachment.objects.create(
            content_object=member,
            file=content,
            name=(answer.get("name") or labels.get(item.key) or "Anlage")[:255],
            description=f"{labels.get(item.key, 'Anlage')} · Aufnahmeantrag #{application.pk}",
            uploaded_by=by,
        )


def _link_or_create_parent(application, row, parent_id):
    values = {field: row.get(field, "") for field in GUARDIAN_FIELDS if row.get(field)}
    if parent_id is None:
        return Parent.objects.create(**values)
    parent = Parent.objects.filter(pk=parent_id, children__departments=application.department_id).distinct().first()
    if parent is None:
        raise ValidationError({"parent_links": "Der gewählte Elternteil gehört nicht zur Abteilung."})
    return parent


def _invite(parents, by):
    from portal.invitations import InvitationError, invite

    for parent in parents:
        try:
            invite(parent, by)
        except InvitationError:
            continue  # no e-mail, already invited or already linked: the portal page shows it
