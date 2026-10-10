"""Shared responses for files after the caller has authorized their owner."""

from pathlib import Path

from django.http import FileResponse, Http404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated


def private_file_response(field, *, filename=None, download=False):
    if not field:
        raise Http404
    try:
        stream = field.open("rb")
        signature = stream.read(16)
        stream.seek(0)
    except (FileNotFoundError, OSError) as exc:
        raise Http404 from exc
    # Never trust the client-supplied MIME type or extension for an inline response.
    content_type = "application/octet-stream"
    if signature.startswith(b"\x89PNG\r\n\x1a\n"):
        content_type = "image/png"
    elif signature.startswith(b"\xff\xd8\xff"):
        content_type = "image/jpeg"
    elif signature.startswith((b"GIF87a", b"GIF89a")):
        content_type = "image/gif"
    elif signature.startswith(b"RIFF") and signature[8:12] == b"WEBP":
        content_type = "image/webp"
    elif signature.startswith(b"%PDF-"):
        content_type = "application/pdf"
    response = FileResponse(
        stream,
        as_attachment=download or content_type == "application/octet-stream",
        filename=filename or Path(field.name).name,
        content_type=content_type,
    )
    response["Cache-Control"] = "private, no-store"
    response["Vary"] = "Cookie, Authorization"
    response["Referrer-Policy"] = "no-referrer"
    response["Content-Security-Policy"] = "sandbox; default-src 'none'"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def private_media_url(kind, pk, request=None):
    from django.urls import reverse

    url = reverse("private-media", kwargs={"kind": kind, "pk": pk})
    return request.build_absolute_uri(url) if request else url


def authorized_owner(view_class, request, pk):
    """Reuse the owning API's current permissions, queryset and object checks."""
    from django.shortcuts import get_object_or_404

    view = view_class()
    view.request = request
    view.action = "retrieve"
    view.kwargs = {"pk": pk}
    if not all(permission.has_permission(request, view) for permission in view.get_permissions()):
        raise Http404
    owner = get_object_or_404(view.get_queryset(), pk=pk)
    view.check_object_permissions(request, owner)
    return owner


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def private_media(request, kind, pk):
    from django.shortcuts import get_object_or_404

    from members.api.viewsets.email_viewsets import EmailMessageViewSet
    from members.api.viewsets.member_viewsets import MemberViewSet
    from members.models import EmailAttachment
    from training.api.viewsets.block import TrainingBlockViewSet
    from training.api.viewsets.library import LibraryBlockViewSet
    from training.api.viewsets.template import TrainingTemplateBlockViewSet
    from training.models import LibraryBlock, TrainingBlock, TrainingMedia, TrainingTemplateBlock
    from users.api_views import UserViewSet

    if kind == "member-avatar":
        return private_file_response(authorized_owner(MemberViewSet, request, pk).avatar)
    if kind == "user-avatar":
        return private_file_response(authorized_owner(UserViewSet, request, pk).avatar)
    if kind == "email-attachment":
        attachment = get_object_or_404(EmailAttachment, pk=pk)
        authorized_owner(EmailMessageViewSet, request, attachment.email_message_id)
        return private_file_response(attachment.file, filename=attachment.original_filename, download=True)
    if kind == "training":
        media = get_object_or_404(TrainingMedia, pk=pk)
        owner = media.content_object
        if isinstance(owner, TrainingBlock):
            authorized_owner(TrainingBlockViewSet, request, owner.pk)
            user = request.user
            if (
                not (user.is_superuser or user.has_perm("departments.can_access_all_departments"))
                and not user.department_roles.filter(department_id=owner.session.department_id).exists()
            ):
                raise Http404
        elif isinstance(owner, LibraryBlock):
            authorized_owner(LibraryBlockViewSet, request, owner.pk)
        elif isinstance(owner, TrainingTemplateBlock):
            authorized_owner(TrainingTemplateBlockViewSet, request, owner.pk)
        else:
            raise Http404
        return private_file_response(media.file, filename=media.original_filename)
    raise Http404
