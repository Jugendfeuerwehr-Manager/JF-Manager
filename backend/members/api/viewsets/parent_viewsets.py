"""
ParentViewSet — CRUD for member parents/guardians.

Scoping: Parents are visible to users who can see at least one of their
children (members). Access is transitive: parent visibility follows the
department memberships of their children.
"""

from django.db.models import Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import clone_request

from departments.mixins import DepartmentScopeViewSetMixin
from jf_manager_backend.permissions import DepartmentRoleModelPermissions
from members.api_serializers import ParentSerializer
from members.models import Parent


@extend_schema_view(
    list=extend_schema(summary="List all parents"),
    retrieve=extend_schema(summary="Get parent details"),
    create=extend_schema(summary="Create new parent"),
    update=extend_schema(summary="Update parent"),
    partial_update=extend_schema(summary="Partially update parent"),
    destroy=extend_schema(summary="Delete parent"),
)
class ParentViewSet(DepartmentScopeViewSetMixin, viewsets.ModelViewSet):
    serializer_class = ParentSerializer
    permission_classes = [IsAuthenticated, DepartmentRoleModelPermissions]
    queryset = Parent.objects.all()  # used by router for basename; actual filtering in get_queryset()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = []
    search_fields = ["name", "lastname", "email", "email2"]
    ordering_fields = ["name", "lastname"]
    ordering = ["lastname", "name"]
    department_field = "children__departments"

    def perform_create(self, serializer):
        # Parent links are validated by the serializer; there is no direct
        # department field to auto-assign through the shared mixin.
        serializer.save()

    def get_serializer(self, *args, **kwargs):
        serializer = super().get_serializer(*args, **kwargs)
        if not kwargs.get("many", False):
            from members.api.viewsets.member_viewsets import MemberViewSet

            member_view = MemberViewSet()
            member_view.request = self.request
            serializer.fields["children"].child_relation.queryset = member_view.get_queryset()
        return serializer

    def _user_is_org_wide(self, user) -> bool:
        return DepartmentScopeViewSetMixin._user_is_org_wide(self, user)

    def _user_department_ids(self, user) -> list:
        return DepartmentScopeViewSetMixin._user_department_ids(self, user)

    def _resolve_requested_department(self, user):
        raw = self.request.query_params.get("department")
        if not raw:
            return None
        try:
            dept_id = int(raw)
        except (ValueError, TypeError) as exc:
            raise ValidationError({"department": "Ungültiger Wert – muss eine Zahl sein."}) from exc
        if self._user_is_org_wide(user):
            return dept_id
        allowed = self._user_department_ids(user)
        if dept_id not in allowed:
            raise PermissionDenied("Sie haben keinen Zugriff auf die angeforderte Abteilung.")
        return dept_id

    def get_queryset(self):
        user = self.request.user
        from members.api.viewsets.member_viewsets import MemberViewSet

        member_view = MemberViewSet()
        member_view.request = clone_request(self.request, "GET")
        visible_children = member_view.get_queryset()
        qs = Parent.objects.prefetch_related(Prefetch("children", queryset=visible_children))

        if self._user_is_org_wide(user):
            requested_dept = self._resolve_requested_department(user)
            if requested_dept is not None:
                # Narrow to parents whose children belong to the requested dept
                qs = qs.filter(children__departments__id=requested_dept)
            return self._filter_by_action_permission(qs.distinct(), user)

        # Department-scoped user: show parents of children in their departments
        allowed_ids = self._user_department_ids(user)
        requested_dept = self._resolve_requested_department(user)

        if requested_dept is not None:
            allowed_ids = [requested_dept]

        # Unassigned contacts have no department for a scoped role to use.
        qs = qs.filter(children__departments__id__in=allowed_ids)
        return self._filter_by_action_permission(qs.distinct(), user)
