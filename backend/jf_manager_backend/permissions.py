from rest_framework.permissions import SAFE_METHODS, BasePermission, DjangoModelPermissions


class CustomDefaultPermissions(DjangoModelPermissions):
    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
        "HEAD": [],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }


class OrgWideWritePermission(BasePermission):
    """
    Read-only access for authenticated users; write access only for org-wide users.

    Org-wide users are:
      - staff
      - superusers
      - users with departments.can_access_all_departments
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        return user.is_staff or user.is_superuser or user.has_perm("departments.can_access_all_departments")


class DepartmentRoleModelPermissions(BasePermission):
    """
    Model-level permissions that accept either:
    - classic Django permissions via user/groups
    - department-role group permissions (scoped roles)
    """

    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
        "HEAD": [],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }

    def _get_model(self, view):
        queryset = getattr(view, "queryset", None)
        if queryset is not None:
            return queryset.model
        return None

    def _department_role_permissions(self, request, department_id=None):
        user = request.user
        roles = user.department_roles.prefetch_related("groups__permissions")

        if department_id is None:
            raw_department = request.query_params.get("department")
            if raw_department:
                try:
                    department_id = int(raw_department)
                except (TypeError, ValueError):
                    return set()
        if department_id is not None:
            roles = roles.filter(department_id=department_id)

        permissions = set()
        for role in roles:
            for group in role.groups.all():
                for perm in group.permissions.all():
                    permissions.add(f"{perm.content_type.app_label}.{perm.codename}")
        return permissions

    def _required_permissions(self, request, view):
        model = self._get_model(view)
        templates = self.perms_map.get(request.method)
        if model is None or templates is None:
            return None
        return [
            template % {"app_label": model._meta.app_label, "model_name": model._meta.model_name}
            for template in templates
        ]

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        required_perms = self._required_permissions(request, view)
        if required_perms is None:
            return False
        role_permissions = self._department_role_permissions(request)
        return all(user.has_perm(permission) or permission in role_permissions for permission in required_perms)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser:
            return True

        required_perms = self._required_permissions(request, view)
        if required_perms is None:
            return False
        # Single-department records must be checked against their real owner,
        # regardless of an absent or manipulated query parameter.
        if not hasattr(obj, "department_id"):
            if hasattr(obj, "departments"):
                object_department_ids = set(obj.departments.values_list("id", flat=True))
            elif obj._meta.label_lower == "members.parent":
                # Read serializers may prefetch only visible children. The
                # permission decision must use every linked child instead.
                object_department_ids = set(
                    obj.children.through.objects.filter(parent_id=obj.pk).values_list(
                        "member__departments__id", flat=True
                    )
                ) - {None}
                if not object_department_ids:
                    return user.has_perm("departments.can_access_all_departments") and all(
                        user.has_perm(permission) for permission in required_perms
                    )
            else:
                return True  # Other object relationships are covered per endpoint.

            if not user.has_perm("departments.can_access_all_departments"):
                object_department_ids &= set(user.department_roles.values_list("department_id", flat=True))
            if not object_department_ids:
                return False
            if all(user.has_perm(permission) for permission in required_perms):
                return True
            return any(
                all(
                    user.has_perm(permission)
                    or permission in self._department_role_permissions(request, department_id)
                    for permission in required_perms
                )
                for department_id in object_department_ids
            )
        if obj.department_id is not None and not (
            user.has_perm("departments.can_access_all_departments")
            or user.department_roles.filter(department_id=obj.department_id).exists()
        ):
            return False
        if all(user.has_perm(permission) for permission in required_perms):
            return True
        if obj.department_id is None:
            return request.method in SAFE_METHODS and all(
                permission in self._department_role_permissions(request) for permission in required_perms
            )

        role_permissions = self._department_role_permissions(request, obj.department_id)
        return all(user.has_perm(permission) or permission in role_permissions for permission in required_perms)
