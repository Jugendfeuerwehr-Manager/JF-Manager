"""Keep independent assignment sources while projecting their union to groups."""

from django.contrib.auth import get_user_model
from django.db import transaction

from departments.models import RoleGrant, UserDepartmentRole


def effective_group_ids(user, department_id):
    if department_id is None:
        return set(user.groups.values_list("pk", flat=True))
    return set(
        UserDepartmentRole.objects.filter(user=user, department_id=department_id).values_list("groups__pk", flat=True)
    ) - {None}


def capture_untracked_local(user, department_id):
    known = set(RoleGrant.objects.filter(user=user, department_id=department_id).values_list("group_id", flat=True))
    for group_id in effective_group_ids(user, department_id) - known:
        RoleGrant.objects.get_or_create(
            user=user, department_id=department_id, group_id=group_id, source="local", source_key=""
        )


def project_sources(user, department_id):
    ids = set(RoleGrant.objects.filter(user=user, department_id=department_id).values_list("group_id", flat=True))
    if department_id is None:
        user.groups.set(ids)
    elif ids:
        role, _ = UserDepartmentRole.objects.get_or_create(user=user, department_id=department_id)
        role.groups.set(ids)
    else:
        # Keep the department membership itself: an empty membership can be
        # intentional and does not confer any model permission.
        role = UserDepartmentRole.objects.filter(user=user, department_id=department_id).first()
        if role:
            role.groups.clear()
    for cache in ("_perm_cache", "_group_perm_cache", "_user_perm_cache", "_prefetched_objects_cache"):
        user.__dict__.pop(cache, None)


@transaction.atomic
def set_local_groups(user, department_id, groups):
    get_user_model().objects.select_for_update().get(pk=user.pk)
    capture_untracked_local(user, department_id)
    ids = {group.pk for group in groups}
    RoleGrant.objects.filter(user=user, department_id=department_id, source="local").exclude(group_id__in=ids).delete()
    for group_id in ids:
        RoleGrant.objects.get_or_create(
            user=user, department_id=department_id, group_id=group_id, source="local", source_key=""
        )
    project_sources(user, department_id)
