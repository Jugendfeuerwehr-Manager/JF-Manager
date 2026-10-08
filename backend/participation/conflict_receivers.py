"""Event triggers for the eligibility re-check (PART-03.5, E11). Every re-check runs after commit."""

from django.db import transaction
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from members.models import Member
from portal.models import AccountLink
from qualifications.models import Qualification, QualificationType, SpecialTask

from .conflicts import recheck
from .models import SessionParticipation


def _later(**scope):
    transaction.on_commit(lambda: recheck(**scope))


def _members_of(instance):
    """The member an entry counts for: its own member or that of the account through a confirmed link (E10)."""
    if instance.member_id:
        return [instance.member_id]
    if instance.user_id:
        return list(
            AccountLink.objects.filter(user_id=instance.user_id, status=AccountLink.Status.CONFIRMED)
            .exclude(member__isnull=True)
            .values_list("member_id", flat=True)
        )
    return []


def _entry_changed(sender, instance, raw=False, **kwargs):
    if raw:
        return
    member_ids = _members_of(instance)
    if member_ids:
        _later(member_ids=member_ids)


for _model in (Qualification, SpecialTask):
    post_save.connect(_entry_changed, sender=_model, dispatch_uid=f"participation-conflict-{_model.__name__}-save")
    post_delete.connect(_entry_changed, sender=_model, dispatch_uid=f"participation-conflict-{_model.__name__}-delete")


@receiver(post_save, sender=Member, dispatch_uid="participation-conflict-member")
def member_saved(sender, instance, raw=False, **kwargs):
    if not raw:
        _later(member_ids=[instance.pk])


@receiver(m2m_changed, sender=Member.departments.through, dispatch_uid="participation-conflict-departments")
def departments_changed(sender, instance, action, reverse=False, pk_set=None, **kwargs):
    if action not in ("post_add", "post_remove", "post_clear"):
        return
    if not reverse:
        _later(member_ids=[instance.pk])
    elif action == "post_clear":
        _later()
    elif pk_set:
        _later(member_ids=list(pk_set))


def _link_changed(sender, instance, raw=False, **kwargs):
    if not raw and instance.member_id:
        _later(member_ids=[instance.member_id])


post_save.connect(_link_changed, sender=AccountLink, dispatch_uid="participation-conflict-link-save")
post_delete.connect(_link_changed, sender=AccountLink, dispatch_uid="participation-conflict-link-delete")


@receiver(m2m_changed, sender=QualificationType.includes.through, dispatch_uid="participation-conflict-hierarchy")
def hierarchy_changed(sender, action, **kwargs):
    if action in ("post_add", "post_remove", "post_clear"):
        _later()


def _participation_changed(sender, instance, raw=False, **kwargs):
    if not raw:
        _later(session_ids=[instance.session_id])


post_save.connect(_participation_changed, sender=SessionParticipation, dispatch_uid="participation-conflict-rule-save")
post_delete.connect(
    _participation_changed, sender=SessionParticipation, dispatch_uid="participation-conflict-rule-delete"
)
