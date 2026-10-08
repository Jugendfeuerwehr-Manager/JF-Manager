"""Which member records a portal account may act for (concept 5.2.3).

Everything a portal endpoint returns about people derives from these sets: the
account's own member record and the minor children of its parent record, both
only through a confirmed AccountLink.
"""

from datetime import date

from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from members.models import Member

from .models import AccountLink, ParentAccessExtension


def eighteen_years_before(today):
    try:
        return today.replace(year=today.year - 18)
    except ValueError:  # 29 February
        return date(today.year - 18, 3, 1)


def confirmed_link(user):
    if not (user and user.is_authenticated):
        return None
    links = AccountLink.objects.select_related("parent", "member")
    return links.filter(user=user, status=AccountLink.Status.CONFIRMED).first()


def visible_children(parent, today=None):
    """Children a parent may still act for: minors, unknown birthday, or a running extension (E6).

    Children without a birthday stay visible until one is recorded.
    """
    today = today or timezone.localdate()
    extended = ParentAccessExtension.objects.filter(parent=parent, member=OuterRef("pk"), until__gte=today)
    return parent.children.filter(
        Q(birthday__isnull=True) | Q(birthday__gt=eighteen_years_before(today)) | Exists(extended)
    ).order_by("name", "pk")


def portal_children(user, today=None):
    """Children of the linked parent record the account may see (see visible_children)."""
    link = confirmed_link(user)
    if link is None or link.parent_id is None:
        return Member.objects.none()
    return visible_children(link.parent, today)


def portal_self(user):
    link = confirmed_link(user)
    return link.member if link else None
