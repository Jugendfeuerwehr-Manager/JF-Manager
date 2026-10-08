"""E19: announce services that became registrable. Detected on TrainingSession status transitions."""

from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from training.models import TrainingSession

from .signals import session_published

PUBLISHED = TrainingSession.Status.PUBLISHED


@receiver(pre_save, sender=TrainingSession, dispatch_uid="participation-remember-status")
def remember_status(sender, instance, raw=False, update_fields=None, **kwargs):
    if raw or (update_fields is not None and "status" not in update_fields):
        instance._participation_previous_status = instance.status
        return
    previous = None
    if instance.pk:
        previous = TrainingSession.objects.filter(pk=instance.pk).values_list("status", flat=True).first()
    instance._participation_previous_status = previous


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
