from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db.models.signals import m2m_changed, pre_delete, pre_save
from django.dispatch import receiver

from departments.models import RoleGrant, UserDepartmentRole
from members.models import Member, Parent

from .access import is_portal_account
from .models import AccountLink

User = get_user_model()

ROLE_DENIED = "Portalzugänge erhalten keine Rollen oder Rechte."


class PortalAccountRoleDenied(PermissionDenied):
    """DRF answers Django's PermissionDenied with 403."""


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


def _deny_portal_users(instance, action, reverse, pk_set):
    """Guard user↔group and user↔permission relations from both sides."""
    if action != "pre_add":
        return
    if not reverse:
        if is_portal_account(instance):
            raise PortalAccountRoleDenied(ROLE_DENIED)
    elif pk_set and User.objects.filter(pk__in=pk_set, account_kind=User.AccountKind.PORTAL).exists():
        raise PortalAccountRoleDenied(ROLE_DENIED)


@receiver(m2m_changed, sender=User.groups.through)
def guard_groups(sender, instance, action, reverse, pk_set, **kwargs):
    _deny_portal_users(instance, action, reverse, pk_set)


@receiver(m2m_changed, sender=User.user_permissions.through)
def guard_permissions(sender, instance, action, reverse, pk_set, **kwargs):
    _deny_portal_users(instance, action, reverse, pk_set)


@receiver(pre_save, sender=UserDepartmentRole)
@receiver(pre_save, sender=RoleGrant)
def guard_role_records(sender, instance, **kwargs):
    if User.objects.filter(pk=instance.user_id, account_kind=User.AccountKind.PORTAL).exists():
        raise PortalAccountRoleDenied(ROLE_DENIED)
