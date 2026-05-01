"""ViewSets for LibraryBlock, LibraryBlockCategory, LibraryBlockTag."""

import io
import os
import uuid as uuid_lib

from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Max
from django_filters.rest_framework import DjangoFilterBackend
from PIL import Image as PilImage
from rest_framework import filters, status, viewsets
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from members.models import Attachment
from training.api.filters import LibraryBlockFilter
from training.api.permissions import CanManageLibrary
from training.api.serializers import (
    LibraryBlockCategorySerializer,
    LibraryBlockDetailSerializer,
    LibraryBlockExportSerializer,
    LibraryBlockListSerializer,
    LibraryBlockTagSerializer,
    TrainingMediaSerializer,
)
from training.models import LibraryBlock, LibraryBlockCategory, LibraryBlockTag, TrainingMedia

# ── Image processing helper (shared with block.py) ────────────────────────────

_MAX_IMAGE_WIDTH = 1200
_JPEG_QUALITY = 85


def _resize_and_optimise(original_file, filename: str):
    """Downscale image to _MAX_IMAGE_WIDTH and re-encode, returning (BytesIO, new_name)."""
    img = PilImage.open(original_file)
    if img.mode in ("P", "LA"):
        img = img.convert("RGBA")
    elif img.mode == "L":
        img = img.convert("RGB")

    if img.width > _MAX_IMAGE_WIDTH:
        ratio = _MAX_IMAGE_WIDTH / img.width
        img = img.resize((int(img.width * ratio), int(img.height * ratio)), PilImage.LANCZOS)

    buf = io.BytesIO()
    if img.mode == "RGBA":
        save_format, ext = "PNG", ".png"
        buf_kwargs: dict = {"optimize": True}
    else:
        save_format, ext = "JPEG", ".jpg"
        buf_kwargs = {"quality": _JPEG_QUALITY, "optimize": True}

    img.save(buf, format=save_format, **buf_kwargs)
    buf.seek(0)
    base = os.path.splitext(filename)[0]
    return buf, f"{base}{ext}"


class LibraryBlockCategoryViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication, TokenAuthentication, SessionAuthentication]
    permission_classes = [CanManageLibrary]
    queryset = LibraryBlockCategory.objects.all()
    serializer_class = LibraryBlockCategorySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]


class LibraryBlockTagViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication, TokenAuthentication, SessionAuthentication]
    permission_classes = [CanManageLibrary]
    queryset = LibraryBlockTag.objects.all()
    serializer_class = LibraryBlockTagSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]


class LibraryBlockViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication, TokenAuthentication, SessionAuthentication]
    permission_classes = [CanManageLibrary]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = LibraryBlockFilter
    search_fields = ["title", "description"]
    ordering_fields = ["title", "created_at", "default_duration_minutes"]
    ordering = ["title"]

    def get_queryset(self):
        return (
            LibraryBlock.objects.select_related("category", "created_by")
            .prefetch_related("tags")
            .annotate(
                usage_count=Count("session_blocks", distinct=True),
                last_used_date=Max("session_blocks__session__date"),
            )
        )

    def get_serializer_class(self):
        if self.action == "list":
            return LibraryBlockListSerializer
        return LibraryBlockDetailSerializer

    @action(detail=True, methods=["get"])
    def usages(self, request, pk=None):
        """
        GET /api/v1/training/library/{id}/usages/
        Returns training sessions where this library block was used.
        """
        from training.api.serializers import TrainingSessionListSerializer

        block = self.get_object()
        sessions = (
            block.session_blocks.select_related("session")
            .order_by("-session__date")
            .values_list("session", flat=True)
            .distinct()
        )
        from training.models import TrainingSession

        qs = TrainingSession.objects.filter(pk__in=sessions).order_by("-date").prefetch_related("groups")
        serializer = TrainingSessionListSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser])
    def upload_image(self, request, pk=None):
        """
        POST /api/v1/training/library/{id}/upload_image/
        Upload an image into the library block's rich-text content.
        """
        block = self.get_object()
        image_file = request.FILES.get("image")
        if not image_file:
            return Response({"detail": "Kein Bild übergeben."}, status=status.HTTP_400_BAD_REQUEST)
        if not image_file.content_type.startswith("image/"):
            return Response({"detail": "Nur Bilddateien erlaubt."}, status=status.HTTP_400_BAD_REQUEST)
        if image_file.size > 20 * 1024 * 1024:
            return Response({"detail": "Bild zu groß (max 20 MB)."}, status=status.HTTP_400_BAD_REQUEST)

        # ── Resize / optimise before saving ──────────────────────────────────
        original_name = image_file.name
        try:
            buf, new_name = _resize_and_optimise(image_file, original_name)
            from django.core.files.uploadedfile import InMemoryUploadedFile

            content_type = "image/jpeg" if new_name.endswith(".jpg") else "image/png"
            image_file = InMemoryUploadedFile(buf, "file", new_name, content_type, buf.getbuffer().nbytes, None)
        except Exception:
            image_file.seek(0)  # fall back to original

        ct = ContentType.objects.get_for_model(block)
        media = TrainingMedia.objects.create(
            content_type=ct,
            object_id=block.pk,
            file=image_file,
            original_filename=original_name,
            uploaded_by=request.user if request.user.is_authenticated else None,
        )
        serializer = TrainingMediaSerializer(media, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def export_blocks(self, request):
        """
        POST /api/v1/training/library/export_blocks/
        Body: {"ids": [1, 2, 3]}
        Returns JSON export package (v1.0 federation format).
        """
        ids = request.data.get("ids", [])
        if not ids:
            return Response({"detail": "Keine IDs angegeben."}, status=status.HTTP_400_BAD_REQUEST)
        blocks = LibraryBlock.objects.filter(pk__in=ids).prefetch_related("tags")
        serializer = LibraryBlockExportSerializer(blocks, many=True, context={"request": request})
        return Response(
            {
                "jf_manager_version": "1.0",
                "export_date": __import__("datetime").datetime.utcnow().isoformat() + "Z",
                "source_instance": request.build_absolute_uri("/"),
                "blocks": serializer.data,
            }
        )

    @action(detail=False, methods=["post"])
    def import_blocks(self, request):
        """
        POST /api/v1/training/library/import_blocks/
        Accepts the v1.0 federation format. Deduplicates by export_uuid.
        """
        data = request.data
        if data.get("jf_manager_version") not in ("1.0",):
            return Response(
                {"detail": "Unbekannte jf_manager_version."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        blocks_data = data.get("blocks", [])
        source_url = data.get("source_instance", "")
        created_count = 0
        updated_count = 0
        errors = []

        for item in blocks_data:
            try:
                export_uuid = uuid_lib.UUID(str(item.get("export_uuid", "")))
            except ValueError:
                errors.append({"block": item.get("title"), "error": "Ungültige UUID"})
                continue

            # Resolve / create category
            category = None
            if item.get("category"):
                category, _ = LibraryBlockCategory.objects.get_or_create(name=item["category"])

            # Resolve / create tags
            tag_names = item.get("tags", [])
            tag_objects = []
            for tag_name in tag_names:
                tag, _ = LibraryBlockTag.objects.get_or_create(name=tag_name)
                tag_objects.append(tag)

            defaults = {
                "title": item.get("title", ""),
                "description": item.get("description", ""),
                "content": item.get("content", ""),
                "default_duration_minutes": item.get("default_duration_minutes", 15),
                "category": category,
                "color": item.get("color", ""),
                "nextcloud_folder_url": item.get("nextcloud_folder_url", ""),
                "source_instance_url": source_url,
            }
            block, created = LibraryBlock.objects.update_or_create(export_uuid=export_uuid, defaults=defaults)
            block.tags.set(tag_objects)
            if created:
                created_count += 1
            else:
                updated_count += 1

        return Response(
            {
                "created": created_count,
                "updated": updated_count,
                "errors": errors,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get", "post", "delete"])
    def attachments(self, request, pk=None):
        """Manage file attachments on a library block."""
        from members.api.serializers import AttachmentSerializer

        block = self.get_object()
        ct = ContentType.objects.get_for_model(block)

        if request.method == "GET":
            attachments = Attachment.objects.filter(content_type=ct, object_id=block.pk)
            serializer = AttachmentSerializer(attachments, many=True, context={"request": request})
            return Response(serializer.data)

        if request.method == "POST":
            data = request.data.copy()
            serializer = AttachmentSerializer(data=data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            serializer.save(
                content_type=ct,
                object_id=block.pk,
                uploaded_by=request.user,
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == "DELETE":
            attachment_id = request.data.get("attachment_id")
            try:
                att = Attachment.objects.get(pk=attachment_id, content_type=ct, object_id=block.pk)
                att.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            except Attachment.DoesNotExist:
                return Response({"detail": "Nicht gefunden."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=["get", "delete"], url_path="media")
    def media(self, request, pk=None):
        """
        GET  /api/v1/training/library/{id}/media/  - list uploaded images for this block
        DELETE /api/v1/training/library/{id}/media/?media_id=X  - remove a single image
        """
        block = self.get_object()
        ct = ContentType.objects.get_for_model(block)

        if request.method == "GET":
            items = TrainingMedia.objects.filter(content_type=ct, object_id=block.pk)
            serializer = TrainingMediaSerializer(items, many=True, context={"request": request})
            return Response(serializer.data)

        if request.method == "DELETE":
            media_id = request.query_params.get("media_id")
            try:
                item = TrainingMedia.objects.get(pk=media_id, content_type=ct, object_id=block.pk)
                if item.file and os.path.isfile(item.file.path):
                    os.remove(item.file.path)
                item.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            except TrainingMedia.DoesNotExist:
                return Response({"detail": "Nicht gefunden."}, status=status.HTTP_404_NOT_FOUND)
