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


def filter_by_permission(queryset, user, permission, department_field="department_id"):
    if user.is_superuser or user.has_perm(permission):
        return queryset
    return queryset.filter(Q(**{f"{department_field}__in": permitted_departments(user, permission)}))
