"""ViewSet for TrainingBlock."""

import os

from django.contrib.contenttypes.models import ContentType
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from members.models import Attachment
from training.api.filters import TrainingBlockFilter
from training.api.permissions import CanManageTraining
from training.api.serializers import (
    TrainingBlockCreateSerializer,
    TrainingBlockMoveSerializer,
    TrainingBlockSerializer,
    TrainingMediaSerializer,
)
from training.models import TrainingBlock, TrainingMedia


class TrainingBlockViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication, TokenAuthentication, SessionAuthentication]
    permission_classes = [CanManageTraining]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = TrainingBlockFilter
    ordering_fields = ['start_offset_minutes', 'position_order', 'title']
    ordering = ['start_offset_minutes', 'position_order']

    def get_queryset(self):
        return TrainingBlock.objects.select_related(
            'session', 'library_block'
        ).prefetch_related('groups')

    def get_serializer_class(self):
        if self.action in ['create']:
            return TrainingBlockCreateSerializer
        if self.action == 'move':
            return TrainingBlockMoveSerializer
        return TrainingBlockSerializer

    @action(detail=True, methods=['patch'])
    def move(self, request, pk=None):
        """
        PATCH /api/v1/training/blocks/{id}/move/
        Update position fields for drag-and-drop in the swimlane planner.
        """
        block = self.get_object()
        serializer = TrainingBlockMoveSerializer(block, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TrainingBlockSerializer(block, context={'request': request}).data)

    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser])
    def upload_image(self, request, pk=None):
        """
        POST /api/v1/training/blocks/{id}/upload_image/
        Upload an image into the block's rich-text content.
        Returns the absolute URL for Tiptap to embed.
        """
        block = self.get_object()
        image_file = request.FILES.get('image')
        if not image_file:
            return Response({'detail': 'Kein Bild übergeben.'}, status=status.HTTP_400_BAD_REQUEST)
        if not image_file.content_type.startswith('image/'):
            return Response({'detail': 'Nur Bilddateien erlaubt.'}, status=status.HTTP_400_BAD_REQUEST)
        if image_file.size > 20 * 1024 * 1024:
            return Response({'detail': 'Bild zu groß (max 20 MB).'}, status=status.HTTP_400_BAD_REQUEST)

        ct = ContentType.objects.get_for_model(block)
        media = TrainingMedia.objects.create(
            content_type=ct,
            object_id=block.pk,
            file=image_file,
            original_filename=image_file.name,
            uploaded_by=request.user if request.user.is_authenticated else None,
        )
        serializer = TrainingMediaSerializer(media, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get', 'post', 'delete'])
    def attachments(self, request, pk=None):
        """Manage file attachments on a training block."""
        from members.api.serializers import AttachmentSerializer
        block = self.get_object()
        ct = ContentType.objects.get_for_model(block)

        if request.method == 'GET':
            attachments = Attachment.objects.filter(content_type=ct, object_id=block.pk)
            serializer = AttachmentSerializer(attachments, many=True, context={'request': request})
            return Response(serializer.data)

        if request.method == 'POST':
            data = request.data.copy()
            serializer = AttachmentSerializer(data=data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            serializer.save(
                content_type=ct,
                object_id=block.pk,
                uploaded_by=request.user,
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            attachment_id = request.data.get('attachment_id')
            try:
                att = Attachment.objects.get(pk=attachment_id, content_type=ct, object_id=block.pk)
                att.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            except Attachment.DoesNotExist:
                return Response({'detail': 'Nicht gefunden.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['get', 'delete'], url_path='media')
    def media(self, request, pk=None):
        """
        GET  /api/v1/training/blocks/{id}/media/  – list all uploaded images for this block
        DELETE /api/v1/training/blocks/{id}/media/?media_id=X  – remove a single media item
        """
        block = self.get_object()
        ct = ContentType.objects.get_for_model(block)

        if request.method == 'GET':
            items = TrainingMedia.objects.filter(content_type=ct, object_id=block.pk)
            serializer = TrainingMediaSerializer(items, many=True, context={'request': request})
            return Response(serializer.data)

        if request.method == 'DELETE':
            media_id = request.query_params.get('media_id')
            try:
                item = TrainingMedia.objects.get(pk=media_id, content_type=ct, object_id=block.pk)
                if item.file and os.path.isfile(item.file.path):
                    os.remove(item.file.path)
                item.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            except TrainingMedia.DoesNotExist:
                return Response({'detail': 'Nicht gefunden.'}, status=status.HTTP_404_NOT_FOUND)
