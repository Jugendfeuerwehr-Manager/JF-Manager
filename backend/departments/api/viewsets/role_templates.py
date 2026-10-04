from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from departments.api.serializers.role_template import RoleTemplateReadSerializer
from departments.models import RoleTemplate
from departments.role_comparison import compare_role_template


class CanViewRoleTemplates(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.has_perm("departments.view_roletemplate")
        )


class RoleTemplateViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = RoleTemplateReadSerializer
    permission_classes = [permissions.IsAuthenticated, CanViewRoleTemplates]
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        return RoleTemplate.objects.select_related("group").order_by("key")

    @action(detail=True, methods=["get"])
    def compare(self, request, pk=None):
        template = self.get_object()
        return Response({**self.get_serializer(template).data, **compare_role_template(template)})
