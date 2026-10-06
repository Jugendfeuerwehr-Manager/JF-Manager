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


def valid_mapping_group(group, department_id, *, allow_archived=False):
    template = getattr(group, "role_template", None)
    return bool(
        template
        and (allow_archived or not template.is_archived)
        and template.scope == ("organization" if department_id is None else "department")
    )


@transaction.atomic
def sync_external_groups(user, source, mappings, matches):
    """Sync verified claims. Mismatch revokes only this mapping's source."""
    get_user_model().objects.select_for_update().get(pk=user.pk)
    existing = RoleGrant.objects.filter(user=user, source=source)
    areas = set(existing.values_list("department_id", flat=True)) | {mapping.department_id for mapping in mappings}
    for area in areas:
        capture_untracked_local(user, area)
    keys = {str(mapping.pk) for mapping in mappings}
    existing.exclude(source_key__in=keys).delete()
    for mapping in mappings:
        key = str(mapping.pk)
        rows = RoleGrant.objects.filter(user=user, source=source, source_key=key)
        if matches(mapping):
            desired = {
                group.pk
                for group in mapping.auth_groups.all()
                if valid_mapping_group(
                    group,
                    mapping.department_id,
                    allow_archived=rows.filter(group=group, department_id=mapping.department_id).exists(),
                )
            }
            rows.exclude(department_id=mapping.department_id, group_id__in=desired).delete()
            for group_id in desired:
                RoleGrant.objects.get_or_create(
                    user=user, group_id=group_id, department_id=mapping.department_id, source=source, source_key=key
                )
        elif mapping.revoke_on_mismatch:
            rows.delete()
        else:
            # Even retained grants must lose removed groups and invalid scopes.
            desired = {
                group.pk
                for group in mapping.auth_groups.all()
                if valid_mapping_group(
                    group,
                    mapping.department_id,
                    allow_archived=rows.filter(group=group, department_id=mapping.department_id).exists(),
                )
            }
            rows.exclude(department_id=mapping.department_id, group_id__in=desired).delete()
    for area in areas:
        project_sources(user, area)


@transaction.atomic
def remove_external_mapping(source, mapping_id):
    """Immediate revocation on mapping deletion; preserve other sources."""
    rows = RoleGrant.objects.filter(source=source, source_key=str(mapping_id))
    affected = list(rows.values_list("user_id", "department_id").distinct())
    users = {
        user.pk: user
        for user in get_user_model()
        .objects.select_for_update()
        .filter(pk__in=[pk for pk, _ in affected])
        .order_by("pk")
    }
    for user_id, area in affected:
        capture_untracked_local(users[user_id], area)
    rows.delete()
    for user_id, area in affected:
        project_sources(users[user_id], area)
