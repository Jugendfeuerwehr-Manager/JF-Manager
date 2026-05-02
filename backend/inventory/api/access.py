from django.db.models import Q


def is_org_wide_user(user) -> bool:
    """Return whether the user may act across all departments without scoping."""
    if not user or not user.is_authenticated:
        return False
    return user.is_staff or user.is_superuser or user.has_perm("departments.can_access_all_departments")


def get_user_department_ids(user) -> set[int]:
    """Return all department ids granted through scoped department-role assignments."""
    if not user or not user.is_authenticated:
        return set()
    return set(user.department_roles.values_list("department_id", flat=True))


def can_manage_department(user, department_id: int | None) -> bool:
    """
    Return whether the user may mutate data owned by the given department.

    Central records remain visible to department-scoped users but mutable only
    by org-wide users.
    """
    if is_org_wide_user(user):
        return True
    if department_id is None:
        # Central/main-org records are visible for everyone but mutable only org-wide.
        return False
    return department_id in get_user_department_ids(user)


def is_location_allowed_for_item_department(location, item_department_id: int | None) -> bool:
    """
    Non-org-wide users may transact only within their owning item department,
    except member personal locations, which can stay department-less.
    """
    location_department_id = getattr(location, "department_id", None)
    if location_department_id == item_department_id:
        return True
    return location_department_id is None and getattr(location, "is_member", False)


def filter_item_department_queryset_for_user(qs, user):
    """
    Filter stock/transaction-like querysets by owning item department.

    These querysets do not carry their own department field, so visibility is
    derived from the linked item or variant parent item. Central items remain
    visible across departments.
    """
    if is_org_wide_user(user):
        return qs

    allowed_ids = get_user_department_ids(user)
    return qs.filter(
        Q(item__isnull=False, item__department_id__in=allowed_ids)
        | Q(item_variant__isnull=False, item_variant__parent_item__department_id__in=allowed_ids)
        | Q(item__isnull=False, item__department__isnull=True)
        | Q(item_variant__isnull=False, item_variant__parent_item__department__isnull=True)
    )
