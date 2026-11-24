from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from departments.mixins import DepartmentScopeViewSetMixin
from membership.api.permissions import MemberRightsPermissions
from membership.api.serializers.events import MembershipEventCorrectionSerializer, MembershipEventSerializer
from membership.models import MembershipEvent


@extend_schema_view(
    list=extend_schema(summary="Membership movements (filter by member, department, kind, year)"),
    partial_update=extend_schema(summary="Correct date, kind, exit reason or note of a movement"),
)
class MembershipEventViewSet(
    DepartmentScopeViewSetMixin, mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    queryset = MembershipEvent.objects.select_related("department", "from_status", "to_status", "created_by")
    permission_classes = [IsAuthenticated, MemberRightsPermissions]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {"member": ["exact"], "department": ["exact"], "kind": ["exact", "in"], "date": ["year"]}
    http_method_names = ["get", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.action == "partial_update":
            return MembershipEventCorrectionSerializer
        return MembershipEventSerializer
