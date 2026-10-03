"""
AttachmentViewSet — file attachments for members and related objects.
"""

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, SAFE_METHODS
from rest_framework.response import Response
from rest_framework.request import clone_request

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

    def get_queryset(self):
        from members.api.viewsets.member_viewsets import MemberViewSet
        from members.api.viewsets.list_viewsets import MemberListViewSet
        from training.api.viewsets.block import TrainingBlockViewSet
        from training.api.viewsets.library import LibraryBlockViewSet

        # An attachment inherits both visibility and edit rights from its owner.
        # Unknown/deleted owners fail closed, including for list and download.
        allowed = Q(pk__in=[])
        owner_request = clone_request(self.request, self.request.method if self.request.method in SAFE_METHODS else "PATCH")
        for view_class in (MemberViewSet, MemberListViewSet, TrainingBlockViewSet, LibraryBlockViewSet):
            owner_view = view_class()
            owner_view.request = owner_request
            owner_view.action = "list" if self.request.method in SAFE_METHODS else "partial_update"
            owner_view.kwargs = {}
            if not all(permission.has_permission(owner_request, owner_view) for permission in owner_view.get_permissions()):
                continue
            owners = owner_view.get_queryset()
            content_type = ContentType.objects.get_for_model(owners.model)
            allowed |= Q(content_type=content_type, object_id__in=owners.values("pk"))
        return super().get_queryset().filter(allowed)

    @extend_schema(summary="Download attachment file")
    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        from django.http import FileResponse

        attachment = self.get_object()
        if attachment.file:
            return FileResponse(attachment.file.open("rb"), as_attachment=True, filename=attachment.name)
        return Response({"detail": "No file attached"}, status=404)
