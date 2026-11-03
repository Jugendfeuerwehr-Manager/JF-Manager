"""Resolve the person a consent belongs to, reusing the owning API's scope."""

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError

SUBJECT_FIELDS = ("member", "parent", "user")


def subject_department_ids(obj, field):
    if field == "user":
        return [None]
    return _department_ids(obj, field)


def _department_ids(obj, field):
    if field == "member":
        ids = list(obj.departments.values_list("id", flat=True))
    else:
        ids = list(obj.children.values_list("departments", flat=True).distinct())
    ids = [pk for pk in ids if pk is not None]
    return ids or [None]


def resolve_subject(request, data, *, write):
    """Return ``(field, obj)`` or raise; members and parents follow their own
    department scope, accounts need the user administration rights."""
    from members.api.viewsets.member_viewsets import MemberViewSet
    from members.api.viewsets.parent_viewsets import ParentViewSet

    given = [field for field in SUBJECT_FIELDS if data.get(field) not in (None, "")]
    if len(given) != 1:
        raise ValidationError({"detail": "Genau eine Person angeben: member, parent oder user."})
    field = given[0]
    try:
        pk = int(data[field])
    except (TypeError, ValueError) as exc:
        raise ValidationError({field: "Ungültige ID."}) from exc

    user = request.user
    if field == "user":
        if pk == user.pk and not write:
            return field, user
        right = "users.change_customuser" if write else "users.view_customuser"
        if not (user.is_superuser or user.has_perm(right)):
            raise PermissionDenied("Keine Berechtigung für Einwilligungen dieses Kontos.")
        return field, get_object_or_404(get_user_model(), pk=pk)

    viewset_class, model_name = (MemberViewSet, "member") if field == "member" else (ParentViewSet, "parent")
    view = viewset_class()
    view.request = request
    view.action = "retrieve"
    view.kwargs = {"pk": pk}
    view.format_kwarg = None
    obj = get_object_or_404(view.get_queryset(), pk=pk)
    right = f"members.{'change' if write else 'view'}_{model_name}"
    if not any(view._has_right_in_department(user, right, dept) for dept in _department_ids(obj, field)):
        raise PermissionDenied("Keine Berechtigung für Einwilligungen dieser Person.")
    return field, obj
