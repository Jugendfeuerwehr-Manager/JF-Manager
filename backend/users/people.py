"""Which accounts count as people (UX-02.1)."""

from django.conf import settings
from django.contrib.auth import get_user_model

# django-guardian creates this system account; it is active but never a person.
ANONYMOUS_USERNAME = getattr(settings, "ANONYMOUS_USER_NAME", None) or "AnonymousUser"


def person_accounts(queryset=None, active_only=True):
    """User accounts that may appear in pickers, rosters and reports."""
    queryset = get_user_model().objects.all() if queryset is None else queryset
    if active_only:
        queryset = queryset.filter(is_active=True)
    return queryset.exclude(username=ANONYMOUS_USERNAME)
