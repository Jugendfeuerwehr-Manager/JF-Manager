"""
AttachmentViewSet — file attachments for members and related objects.
"""
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from members.api_serializers import AttachmentSerializer
from members.models import Attachment


@extend_schema_view(
    list=extend_schema(summary="List all attachments"),
    retrieve=extend_schema(summary="Get attachment details"),
    create=extend_schema(summary="Create new attachment"),
    update=extend_schema(summary="Update attachment"),
    partial_update=extend_schema(summary="Partially update attachment"),
    destroy=extend_schema(summary="Delete attachment")
)
class AttachmentViewSet(viewsets.ModelViewSet):
    queryset = Attachment.objects.all().order_by('-uploaded_at')
    serializer_class = AttachmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['content_type', 'object_id']
    ordering_fields = ['uploaded_at', 'name']
    ordering = ['-uploaded_at']

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)

    @extend_schema(summary="Download attachment file")
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        from django.http import FileResponse
        attachment = self.get_object()
        if attachment.file:
            response = FileResponse(attachment.file.open('rb'))
            response['Content-Disposition'] = f'attachment; filename="{attachment.name}"'
            return response
        return Response({"detail": "No file attached"}, status=404)
