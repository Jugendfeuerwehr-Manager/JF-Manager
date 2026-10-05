"""Register signed-in devices and let users end their other sessions."""

from django.contrib.auth.signals import user_logged_in
from django.contrib.sessions.models import Session
from django.dispatch import receiver
from django.utils import timezone

from users.models import UserSession

USER_AGENT_LENGTH = 200


@receiver(user_logged_in)
def register_device(sender, request, user, **kwargs):
    session = getattr(request, "session", None)
    if session is None:
        return
    if not session.session_key:
        # login() flushed a previous user's session; persist the new one first.
        session.save()
    record = Session.objects.filter(session_key=session.session_key).first()
    if record is None:
        return
    UserSession.objects.update_or_create(
        session=record,
        defaults={
            "user": user,
            "user_agent": request.META.get("HTTP_USER_AGENT", "")[:USER_AGENT_LENGTH],
            "last_seen_at": timezone.now(),
        },
    )


def touch_device(session_key):
    if session_key:
        UserSession.objects.filter(session_id=session_key).update(last_seen_at=timezone.now())


def active_devices(user):
    return UserSession.objects.filter(user=user, session__expire_date__gt=timezone.now()).select_related("session")


def end_device(device):
    # Deleting the session row removes the device entry by cascade.
    Session.objects.filter(session_key=device.session_id).delete()
