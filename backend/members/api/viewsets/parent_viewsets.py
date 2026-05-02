"""
ParentViewSet — CRUD for member parents/guardians.

Scoping: Parents are visible to users who can see at least one of their
children (members). Access is transitive: parent visibility follows the
department memberships of their children.
"""

from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated

from departments.mixins import DepartmentScopeViewSetMixin
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
class ParentViewSet(viewsets.ModelViewSet):
    serializer_class = ParentSerializer
    permission_classes = [IsAuthenticated]
    queryset = Parent.objects.all()  # used by router for basename; actual filtering in get_queryset()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = []
    search_fields = ["name", "lastname", "email", "email2"]
    ordering_fields = ["name", "lastname"]
    ordering = ["lastname", "name"]

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
        qs = Parent.objects.prefetch_related("children")

        if self._user_is_org_wide(user):
            requested_dept = self._resolve_requested_department(user)
            if requested_dept is not None:
                # Narrow to parents whose children belong to the requested dept
                qs = qs.filter(children__departments__id=requested_dept)
            return qs.distinct()

        # Department-scoped user: show parents of children in their departments
        allowed_ids = self._user_department_ids(user)
        requested_dept = self._resolve_requested_department(user)

        if requested_dept is not None:
            allowed_ids = [requested_dept]

        # Parents whose children have at least one matching department,
        # OR parents with no children at all (department-agnostic orphans)
        qs = qs.filter(Q(children__departments__id__in=allowed_ids) | Q(children__isnull=True))
        return qs.distinct()
