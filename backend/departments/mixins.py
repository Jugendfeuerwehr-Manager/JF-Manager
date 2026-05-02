"""
DepartmentScopeViewSetMixin

Apply this mixin to any ViewSet that should be scoped by department.

Usage:
    class MyViewSet(DepartmentScopeViewSetMixin, viewsets.ModelViewSet):
        # The model field pointing at Department (default: 'department')
        department_field = 'department'
        # Whether records with department=NULL are shown to dept-scoped users
        include_central_records = False
        ...

The mixin overrides get_queryset() to transparently filter results.
It also hooks into perform_create() to auto-assign the active department.

Org-wide access conditions (no filtering applied):
  - user.is_staff is True
  - user.has_perm('departments.can_access_all_departments') is True

Optional query param ?department=<id> lets org-wide users additionally filter
to one specific department.  Dept-scoped users can only request departments
they actually belong to.
"""

from rest_framework.exceptions import PermissionDenied, ValidationError


class DepartmentScopeViewSetMixin:
    """Mixin for department-aware filtering in DRF ViewSets."""

    # Name of the ForeignKey / M2M field on the model pointing at Department.
    # Override in the ViewSet if the field has a different name.
    department_field: str = "department"

    # Whether records whose department is NULL (central/unassigned) should be
    # included in the results for dept-scoped users.
    # Default False: once a user is assigned to departments, they only see
    # records explicitly scoped to one of their departments.
    # Set to True on a ViewSet to also surface "org-wide" central records.
    include_central_records: bool = False

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _user_is_org_wide(self, user) -> bool:
        """Return True if the user has unrestricted cross-department access."""
        return user.is_staff or user.is_superuser or user.has_perm("departments.can_access_all_departments")

    def _user_department_ids(self, user) -> list:
        """Return list of department PKs the user is explicitly assigned to."""
        return list(user.department_roles.values_list("department_id", flat=True))

    def _resolve_requested_department(self, user):
        """
        Parse and validate the ?department= query param.

        Returns:
          - int   : a specific department PK (validated for access)
          - None  : no filter requested
        Raises PermissionDenied if the user requests a dept they can't access.
        """
        raw = self.request.query_params.get("department")
        if not raw:
            return None

        try:
            dept_id = int(raw)
        except (ValueError, TypeError) as exc:
            raise ValidationError({"department": "Ungültiger Wert – muss eine Zahl sein."}) from exc

        if self._user_is_org_wide(user):
            return dept_id  # org-wide users may filter to any dept

        allowed = self._user_department_ids(user)
        if dept_id not in allowed:
            raise PermissionDenied("Sie haben keinen Zugriff auf die angeforderte Abteilung.")
        return dept_id

    # ------------------------------------------------------------------ #
    # get_queryset                                                         #
    # ------------------------------------------------------------------ #

    def get_queryset(self):
        """
        Scope list/detail access by the caller's department context.

        Important nuance for department-scoped users:
        when ``include_central_records`` is enabled we keep department=NULL
        records visible even if the frontend sends ``?department=<active_id>``.
        The active department acts as the editable context, not as a request to
        hide central records from that user.
        """
        qs = super().get_queryset()
        user = self.request.user
        requested_dept = self._resolve_requested_department(user)

        if self._user_is_org_wide(user):
            # Org-wide: optionally narrow to a single dept
            if requested_dept is not None:
                qs = qs.filter(**{self.department_field: requested_dept})
            return qs

        # Department-scoped user
        allowed_ids = self._user_department_ids(user)

        if self.include_central_records:
            # Include items from their departments AND central (null) items
            dept_filter = {f"{self.department_field}__in": allowed_ids}
            null_filter = {f"{self.department_field}__isnull": True}
            from django.db.models import Q

            qs = qs.filter(Q(**dept_filter) | Q(**null_filter))
        else:
            qs = qs.filter(**{f"{self.department_field}__in": allowed_ids})

        # Allow further narrowing to a specific permitted dept
        if requested_dept is not None:
            if self.include_central_records:
                from django.db.models import Q

                qs = qs.filter(
                    Q(**{self.department_field: requested_dept}) | Q(**{f"{self.department_field}__isnull": True})
                )
            else:
                qs = qs.filter(**{self.department_field: requested_dept})

        return qs

    # ------------------------------------------------------------------ #
    # perform_create                                                       #
    # ------------------------------------------------------------------ #

    def perform_create(self, serializer):
        """
        Auto-assign the active department on creation if not explicitly provided.

        If the user is dept-scoped and no department was submitted, the first
        (or sole) department from ?department= or the user's assignment list is
        used.  Org-wide users must explicitly set a department or leave it null.
        """
        user = self.request.user
        kwargs = {}

        # Only auto-assign when the field is not already set by the serializer
        if self.department_field not in serializer.validated_data:
            requested_dept = self._resolve_requested_department(user)
            import contextlib

            from departments.models import Department

            if requested_dept is not None:
                with contextlib.suppress(Department.DoesNotExist):
                    kwargs[self.department_field] = Department.objects.get(pk=requested_dept)
            elif not self._user_is_org_wide(user):
                allowed_ids = self._user_department_ids(user)
                if len(allowed_ids) == 1:
                    with contextlib.suppress(Department.DoesNotExist):
                        kwargs[self.department_field] = Department.objects.get(pk=allowed_ids[0])

        serializer.save(**kwargs)
