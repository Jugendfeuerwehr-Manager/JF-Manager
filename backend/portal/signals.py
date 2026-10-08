from django.db.models.signals import pre_delete
from django.dispatch import receiver

from members.models import Member, Parent

from .models import AccountLink


def _release(field, instance):
    """Drop a link that would point at nothing; otherwise detach the deleted record."""
    other = "member" if field == "parent" else "parent"
    links = AccountLink.objects.filter(**{field: instance})
    links.filter(**{f"{other}__isnull": True}).delete()
    links.update(**{field: None})


@receiver(pre_delete, sender=Parent)
def release_parent_link(sender, instance, **kwargs):
    _release("parent", instance)


@receiver(pre_delete, sender=Member)
def release_member_link(sender, instance, **kwargs):
    _release("member", instance)
