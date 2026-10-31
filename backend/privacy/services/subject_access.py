"""Copy of all data about one person (Art. 15 and 20 DSGVO) as a ZIP: JSON plus files."""

import io
import json
import zipfile
from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from django.db.models.fields.files import FieldFile
from django.utils import timezone

README = """Auskunft nach Art. 15 DSGVO

daten.json enthält alle zu dieser Person gespeicherten Daten, gegliedert nach Bereichen.
Der Ordner dateien/ enthält hochgeladene Dateien (Bild, Anhänge).
Erstellt am {created}.
"""


def _value(obj, field):
    value = getattr(obj, field.attname)
    if value is None:
        return None
    if field.is_relation:
        related = getattr(obj, field.name, None)
        return {"id": value, "bezeichnung": str(related) if related is not None else None}
    if isinstance(value, FieldFile):
        return value.name or None
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, (Decimal, UUID)):
        return str(value)
    if hasattr(value, "as_e164"):  # phone numbers
        return str(value)
    return value


def row(obj, skip=()):
    return {field.name: _value(obj, field) for field in obj._meta.concrete_fields if field.name not in skip}


def rows(queryset, skip=()):
    return [row(obj, skip) for obj in queryset]


def _common(field, subject):
    from portal.models import AccountLink
    from privacy.models import ConsentRecord

    link = AccountLink.objects.filter(**{field: subject}).select_related("user").first() if field != "user" else None
    return {
        "einwilligungen": rows(ConsentRecord.objects.filter(**{field: subject})),
        "portalzugang": {"benutzername": link.user.username, "aktiv": link.user.is_active} if link else None,
    }


def member_data(member):
    from members.models import EmailRecipient, Event, MemberListEntry
    from orders.models import Order
    from participation.models import Registration
    from portal.models import ChangeLog
    from qualifications.models import Qualification, SpecialTask
    from servicebook.models import Attendance

    return {
        "stammdaten": row(member),
        "abteilungen": [str(department) for department in member.departments.all()],
        "eltern": rows(member.parent_set.all()),
        "verlauf": rows(Event.objects.filter(member=member)),
        "anwesenheit": rows(Attendance.objects.filter(person=member).select_related("service")),
        "teilnahme": rows(Registration.objects.filter(member=member).select_related("session")),
        "qualifikationen": rows(Qualification.objects.filter(member=member).select_related("type")),
        "sonderaufgaben": rows(SpecialTask.objects.filter(member=member)),
        "bestellungen": rows(Order.objects.filter(member=member)),
        "listen": rows(MemberListEntry.objects.filter(member=member).select_related("member_list")),
        "emails": rows(
            EmailRecipient.objects.filter(member=member).select_related("email_message"),
            skip=("personalized_body_html",),
        ),
        "aenderungsprotokoll": rows(ChangeLog.objects.filter(target_kind="member", target_id=member.pk)),
        **_common("member", member),
    }


def parent_data(parent):
    from django.db.models import Q

    from members.models import EmailRecipient
    from portal.models import ChangeLog

    addresses = [address for address in (parent.email, parent.email2) if address]
    emails = (
        EmailRecipient.objects.filter(Q(email_address__in=addresses)) if addresses else EmailRecipient.objects.none()
    )
    return {
        "stammdaten": row(parent),
        "kinder": [{"id": child.pk, "name": child.get_full_name()} for child in parent.children.all()],
        "emails": rows(emails.select_related("email_message"), skip=("personalized_body_html",)),
        "aenderungsprotokoll": rows(ChangeLog.objects.filter(target_kind="parent", target_id=parent.pk)),
        **_common("parent", parent),
    }


def user_data(user):
    from users.models import UserSession

    return {
        "konto": row(user, skip=("password",)),
        "abteilungsrollen": [
            {"abteilung": str(role.department), "gruppen": [group.name for group in role.groups.all()]}
            for role in user.department_roles.select_related("department").prefetch_related("groups")
        ],
        "sitzungen": rows(UserSession.objects.filter(user=user), skip=("session_id",)),
        **_common("user", user),
    }


def _files(field, subject):
    if field == "member":
        if subject.avatar:
            yield "bild", subject.avatar
        for attachment in subject.attachments.all():
            yield f"anhang-{attachment.pk}", attachment.file
    elif field == "user" and subject.avatar:
        yield "bild", subject.avatar


def build_archive(field, subject):
    builders = {"member": member_data, "parent": parent_data, "user": user_data}
    data = builders[field](subject)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("LIESMICH.txt", README.format(created=timezone.localtime().strftime("%d.%m.%Y %H:%M")))
        archive.writestr("daten.json", json.dumps(data, ensure_ascii=False, indent=2, default=str))
        for name, file in _files(field, subject):
            try:
                with file.open("rb") as handle:
                    suffix = file.name.rsplit(".", 1)[-1] if "." in file.name else "bin"
                    archive.writestr(f"dateien/{name}.{suffix}", handle.read())
            except (FileNotFoundError, OSError):
                continue
    return buffer.getvalue()
