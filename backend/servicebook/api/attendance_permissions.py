from django.db.models import Q


def permitted_departments(user, permission):
    """Department IDs in which a role grants one concrete model permission."""
    app_label, codename = permission.split(".", 1)
    return user.department_roles.filter(
        groups__permissions__codename=codename,
        groups__permissions__content_type__app_label=app_label,
    ).values_list("department_id", flat=True)


def has_department_permission(user, permission, department_id):
    if user.is_superuser or user.has_perm(permission):
        return True
    if department_id is None:
        return False
    return permitted_departments(user, permission).filter(department_id=department_id).exists()


def filter_by_permission(queryset, user, permission, department_field="department_id", include_central=False):
    if user.is_superuser or user.has_perm(permission):
        return queryset
    departments = permitted_departments(user, permission)
    scope = Q(**{f"{department_field}__in": departments})
    if include_central and departments.exists():
        # Services for the whole organisation (department=NULL) concern every department.
        scope |= Q(**{f"{department_field}__isnull": True})
    return queryset.filter(scope)


def attendance_departments(user, service, permission):
    """Departments whose people ``user`` may handle on ``service`` with ``permission``.

    ``None`` means everybody on the roster. A service for the whole organisation
    (department=NULL) is shared: department roles act on their own people there.
    An empty set means no access.
    """
    if user.is_superuser or user.has_perm(permission):
        return None
    if service.department_id is not None:
        return {service.department_id} if has_department_permission(user, permission, service.department_id) else set()
    return set(permitted_departments(user, permission))
