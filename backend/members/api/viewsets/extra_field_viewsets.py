from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from departments.mixins import DepartmentScopeViewSetMixin
from jf_manager_backend.mixins import BasePermissionedViewSet
from members.api.serializers.extra_field_serializers import MemberFieldDefinitionSerializer
from members.models import MemberFieldDefinition


@extend_schema_view(
    list=extend_schema(summary="Additional member fields (own departments and organisation-wide)"),
    create=extend_schema(summary="Create an additional member field"),
    destroy=extend_schema(summary="Delete an unused additional member field"),
)
class MemberFieldDefinitionViewSet(DepartmentScopeViewSetMixin, BasePermissionedViewSet, viewsets.ModelViewSet):
    queryset = MemberFieldDefinition.objects.all()
    serializer_class = MemberFieldDefinitionSerializer
    # No "department" filter: the scope mixin reads ?department= and keeps organisation fields.
    filterset_fields = ["active"]
    ordering = ["position", "label"]
    # Organisation-wide fields apply to every department; writing stays with the owner.
    include_central_records = True

    def get_permissions(self):
        # Field definitions carry no personal data; every staff account reads them to show
        # members. Writing follows the model rights in the owning department.
        from portal.permissions import StaffAccountRequired

        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [IsAuthenticated(), StaffAccountRequired()]
        return super().get_permissions()

    def _filter_by_action_permission(self, qs, user):
        # Reading stays limited to the caller's departments and the organisation (get_queryset);
        # it needs no model right, see get_permissions.
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return qs
        return super()._filter_by_action_permission(qs, user)

    def perform_create(self, serializer):
        self._validate_target_department(serializer)
        serializer.save()

    def perform_update(self, serializer):
        self._validate_target_department(serializer)
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        definition = self.get_object()
        if MemberFieldDefinitionSerializer().get_in_use(definition):
            return Response(
                {"detail": "Mitglieder haben schon Angaben in diesem Feld. Es lässt sich nur deaktivieren."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)
