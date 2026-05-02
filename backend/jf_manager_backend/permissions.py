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

    def _department_role_codenames(self, request):
        user = request.user
        roles = user.department_roles.prefetch_related("groups__permissions")

        raw_department = request.query_params.get("department")
        if raw_department:
            try:
                dept_id = int(raw_department)
                roles = roles.filter(department_id=dept_id)
            except (TypeError, ValueError):
                pass

        codenames = set()
        for role in roles:
            for group in role.groups.all():
                for perm in group.permissions.all():
                    codenames.add(perm.codename)
        return codenames

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_staff or user.is_superuser or user.has_perm("departments.can_access_all_departments"):
            return True

        model = self._get_model(view)
        if model is None:
            return True

        required_perms = self.perms_map.get(request.method, [])
        if not required_perms:
            return True

        app_label = model._meta.app_label
        model_name = model._meta.model_name
        role_codenames = self._department_role_codenames(request)

        for perm_tmpl in required_perms:
            perm_name = perm_tmpl % {"app_label": app_label, "model_name": model_name}
            codename = perm_name.split(".", 1)[1]
            if user.has_perm(perm_name):
                continue
            if codename in role_codenames:
                continue
            return False

        return True
