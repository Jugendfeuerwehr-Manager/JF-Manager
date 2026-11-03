"""Need-to-know for member fields (DSGVO): reading a member does not mean seeing everything.

Contact data and sensitive fields need their own right in one of the member's
departments. Health notes never travel with the member; they have their own
endpoint with a fresh confirmation.
"""

CONTACT_FIELDS = ("email", "street", "zip_code", "city", "phone", "mobile")
SENSITIVE_FIELDS = ("notes", "identityCardNumber", "canSwimm")
FIELD_RIGHTS = {
    "members.view_member_contact": CONTACT_FIELDS,
    "members.view_member_sensitive": SENSITIVE_FIELDS,
    # Only whether health notes exist; the text has its own endpoint.
    "members.view_member_health": ("has_health_notes",),
}


def has_member_right(user, member, permission, cache=None):
    """``permission`` in at least one of the member's departments (central: organisation-wide)."""
    from departments.mixins import DepartmentScopeViewSetMixin

    if not (user and user.is_authenticated):
        return False
    if user.is_superuser:
        return True
    department_ids = tuple(sorted(d.pk for d in member.departments.all())) or (None,)
    key = (permission, department_ids)
    if cache is not None and key in cache:
        return cache[key]
    scope = DepartmentScopeViewSetMixin()
    allowed = any(scope._has_right_in_department(user, permission, d) for d in department_ids)
    if cache is not None:
        cache[key] = allowed
    return allowed


def hidden_fields(member, context):
    request = context.get("request")
    user = getattr(request, "user", None)
    cache = context.setdefault("_member_field_rights", {})
    hidden = set()
    for permission, fields in FIELD_RIGHTS.items():
        if not has_member_right(user, member, permission, cache):
            hidden.update(fields)
    return hidden


class MemberFieldAccessMixin:
    """Drop fields the caller may not see from output, and ignore them on writes."""

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if isinstance(instance, self.Meta.model) and self.context.get("request") is not None:
            for field in hidden_fields(instance, self.context):
                data.pop(field, None)
        return data

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context.get("request")
        if request is None:
            return attrs
        if self.instance is not None:
            hidden = hidden_fields(self.instance, self.context)
        else:
            # New members: the rights must exist in a department the member will belong to.
            user = request.user
            departments = attrs.get("departments") or []
            from departments.mixins import DepartmentScopeViewSetMixin

            scope = DepartmentScopeViewSetMixin()
            ids = [d.pk for d in departments] or [None]
            hidden = {
                field
                for permission, fields in FIELD_RIGHTS.items()
                if not (user.is_superuser or any(scope._has_right_in_department(user, permission, d) for d in ids))
                for field in fields
            }
        for field in hidden:
            attrs.pop(field, None)
        return attrs
