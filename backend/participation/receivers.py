"""E19: announce services that became registrable. Detected on TrainingSession status transitions."""

from datetime import datetime

from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from training.models import TrainingSession

from . import changes
from .signals import session_changed, session_published

PUBLISHED = TrainingSession.Status.PUBLISHED


@receiver(pre_save, sender=TrainingSession, dispatch_uid="participation-remember-status")
def remember_status(sender, instance, raw=False, update_fields=None, **kwargs):
    """Remember status and schedule as stored before this save (``_participation_before``)."""
    tracked = set(changes.TRACKED)
    if raw or (update_fields is not None and not tracked & set(update_fields)):
        instance._participation_previous_status = instance.status
        instance._participation_before = None
        return
    before = None
    if instance.pk:
        before = TrainingSession.objects.filter(pk=instance.pk).values(*changes.TRACKED).first()
    instance._participation_before = before
    instance._participation_previous_status = before["status"] if before else None


@receiver(post_save, sender=TrainingSession, dispatch_uid="participation-announce-published")
def announce_published(sender, instance, created, raw=False, **kwargs):
    if raw or instance.status != PUBLISHED:
        return
    if getattr(instance, "_participation_previous_status", None) == PUBLISHED:
        return
    # Services that already started or hidden from the portal are not announced.
    from .service import participation_for, session_start

    try:
        started = session_start(instance) <= timezone.now()
    except (TypeError, ValueError):  # date/time still given as strings: nothing to announce reliably
        return
    if started or not participation_for(instance)[0].portal_visible:
        return
    transaction.on_commit(lambda: session_published.send(sender=TrainingSession, session=instance))


def _view(values):
    return {
        "date": values["date"],
        "start_time": values["start_time"],
        "end_time": values["end_time"],
        "place": values["location"],
    }


@receiver(post_save, sender=TrainingSession, dispatch_uid="participation-announce-changed")
def announce_changed(sender, instance, created, raw=False, **kwargs):
    """Moved, changed (place) or cancelled services keep their registrations; NOTIF-01 hears about it."""
    before = getattr(instance, "_participation_before", None)
    if raw or created or not before:
        return
    now_values = changes.snapshot_values(instance)
    schedule = ("date", "start_time", "end_time")
    moved = any(before[name] != now_values[name] for name in schedule)
    place = before["location"] != now_values["location"]
    if moved:
        # Explicit deadlines may not lie behind the new start; derived ones follow by themselves.
        changes.cap_explicit_deadlines(instance)
    was_published = before["status"] == PUBLISHED
    if not was_published:
        return
    if now_values["status"] == TrainingSession.Status.CANCELLED:
        kind = "cancelled"
    elif now_values["status"] == PUBLISHED and (moved or place):
        kind = "moved" if moved else "changed"
    else:
        return
    from .service import participation_for

    participation = participation_for(instance)[0]
    # Services that already started (by their stored start) are history; hidden ones are not announced.
    started = timezone.make_aware(datetime.combine(before["date"], before["start_time"])) <= timezone.now()
    if started or not participation.portal_visible:
        return
    old, new, mode = _view(before), _view(now_values), participation.mode
    transaction.on_commit(
        lambda: session_changed.send(
            sender=TrainingSession,
            session=instance,
            kind=kind,
            old=old,
            new=new,
            member_ids=changes.affected_member_ids(instance, mode),
        )
    )
