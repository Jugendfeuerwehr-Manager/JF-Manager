from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone

from members.models import Member
from participation.models import SessionParticipation
from training.models import TrainingSession

BERLIN = ZoneInfo("Europe/Berlin")


def berlin(*args):
    return datetime(*args, tzinfo=BERLIN)


def make_session(
    department, *, day=date(2030, 3, 12), start=time(18), end=time(20), groups=(), status="published", **kw
):
    session = TrainingSession.objects.create(
        title=kw.pop("title", "Übung"),
        date=day,
        start_time=start,
        end_time=end,
        department=department,
        status=status,
        **kw,
    )
    session.groups.set(groups)
    return session


def configure(session, **values):
    row, _ = SessionParticipation.objects.update_or_create(session=session, defaults=values)
    return row


def make_member(department, name="Mia", group=None, **kw):
    member = Member.objects.create(name=name, lastname="Test", group=group, **kw)
    member.departments.add(department)
    return member


def future_day(days=10):
    return timezone.localdate() + timedelta(days=days)
