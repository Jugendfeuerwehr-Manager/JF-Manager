"""
AttachmentViewSet — file attachments for members and related objects.
"""

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS, IsAuthenticated
from rest_framework.request import clone_request
from rest_framework.response import Response

from members.api_serializers import AttachmentSerializer
from members.models import Attachment


@extend_schema_view(
    list=extend_schema(summary="List all attachments"),
    retrieve=extend_schema(summary="Get attachment details"),
    create=extend_schema(summary="Create new attachment"),
    update=extend_schema(summary="Update attachment"),
    partial_update=extend_schema(summary="Partially update attachment"),
    destroy=extend_schema(summary="Delete attachment"),
)
class AttachmentViewSet(viewsets.ModelViewSet):
    queryset = Attachment.objects.all().order_by("-uploaded_at")
    serializer_class = AttachmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["content_type", "object_id"]
    ordering_fields = ["uploaded_at", "name"]
    ordering = ["-uploaded_at"]

    # Creation belongs to the owning object's attachment action, which resolves
    # and authorizes the generic relation. Never accept arbitrary content types.
    http_method_names = ["get", "patch", "put", "delete", "head", "options"]

    @staticmethod
    def _owner_views():
        """Owner model -> the viewset whose rights govern its attachments."""
        from members.api.viewsets.list_viewsets import MemberListViewSet
        from members.api.viewsets.member_viewsets import MemberViewSet
        from members.models import Member, MemberList
        from qualifications.api.viewsets import QualificationViewSet, SpecialTaskViewSet
        from qualifications.models import Qualification, SpecialTask
        from training.api.viewsets.block import TrainingBlockViewSet
        from training.api.viewsets.library import LibraryBlockViewSet
        from training.api.viewsets.template import TrainingTemplateBlockViewSet
        from training.models import LibraryBlock, TrainingBlock, TrainingTemplateBlock

        return {
            Member: MemberViewSet,
            MemberList: MemberListViewSet,
            TrainingBlock: TrainingBlockViewSet,
            LibraryBlock: LibraryBlockViewSet,
            TrainingTemplateBlock: TrainingTemplateBlockViewSet,
            Qualification: QualificationViewSet,
            SpecialTask: SpecialTaskViewSet,
        }

    def _owner_view(self, view_class, method, action):
        owner_view = view_class()
        owner_view.request = clone_request(self.request, method)
        owner_view.action = action
        owner_view.kwargs = {}
        owner_view.format_kwarg = None
        return owner_view

    def get_queryset(self):
        from members.api.viewsets.member_viewsets import MemberViewSet
        from training.api.viewsets.block import TrainingBlockViewSet

        # An attachment inherits both visibility and edit rights from its owner.
        # Unknown/deleted owners fail closed, including for list and download.
        allowed = Q(pk__in=[])
        safe = self.request.method in SAFE_METHODS
        for view_class in self._owner_views().values():
            owner_view = self._owner_view(
                view_class, self.request.method if safe else "PATCH", "list" if safe else "partial_update"
            )
            owner_request = owner_view.request
            if not all(
                permission.has_permission(owner_request, owner_view) for permission in owner_view.get_permissions()
            ):
                continue
            owners = owner_view.get_queryset()
            if view_class is TrainingBlockViewSet:
                user = self.request.user
                if not (user.is_superuser or user.has_perm("departments.can_access_all_departments")):
                    owners = owners.filter(session__department_id__in=user.department_roles.values("department_id"))
            if view_class is MemberViewSet and self.request.method not in SAFE_METHODS:
                user = self.request.user
                if not (owner_view._user_is_org_wide(user) and user.has_perm("members.change_member")):
                    if user.has_perm("members.change_member"):
                        permitted_ids = set(owner_view._user_department_ids(user))
                    else:
                        permitted_ids = set(
                            user.department_roles.filter(
                                groups__permissions__content_type__app_label="members",
                                groups__permissions__codename="change_member",
                            ).values_list("department_id", flat=True)
                        )
                    owners = owners.filter(departments__id__in=permitted_ids).distinct()
            content_type = ContentType.objects.get_for_model(owners.model)
            allowed |= Q(content_type=content_type, object_id__in=owners.values("pk"))
        return super().get_queryset().filter(allowed)

    def get_object(self):
        attachment = super().get_object()
        if self.request.method not in SAFE_METHODS:
            self._check_owner_write(attachment)
        return attachment

    def _check_owner_write(self, attachment):
        """Writes need the owner's own object check, e.g. the change right in
        the department of a qualification's member, not mere visibility."""
        owner = attachment.content_object
        view_class = self._owner_views().get(type(owner)) if owner is not None else None
        if view_class is None:
            raise PermissionDenied("Der Anhang gehört zu keinem bearbeitbaren Datensatz.")
        owner_view = self._owner_view(view_class, "PATCH", "partial_update")
        for permission in owner_view.get_permissions():
            if not (
                permission.has_permission(owner_view.request, owner_view)
                and permission.has_object_permission(owner_view.request, owner_view, owner)
            ):
                raise PermissionDenied("Keine Berechtigung, diesen Datensatz zu ändern.")

    @extend_schema(summary="Download attachment file")
    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        from jf_manager_backend.private_media import private_file_response

        attachment = self.get_object()
        if attachment.file:
            return private_file_response(attachment.file, download=True, filename=attachment.name)
        return Response({"detail": "No file attached"}, status=404)
