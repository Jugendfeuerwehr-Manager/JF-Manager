from django.core import signing
from django.http import Http404
from django.urls import reverse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from jf_manager_backend.private_media import private_file_response
from members.models import Attachment

SALT = "jf-attachment-preview-v1"


def preview_url(attachment):
    token = signing.dumps([attachment.pk, attachment.file.name], salt=SALT)
    return reverse("attachment-preview", kwargs={"pk": attachment.pk, "token": token})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def attachment_preview(request, pk, token):
    try:
        signed_id, file_name = signing.loads(token, salt=SALT, max_age=300)
        attachment = Attachment.objects.get(pk=pk)
        if signed_id != attachment.pk or not attachment.file or file_name != attachment.file.name:
            raise Http404
    except (signing.BadSignature, signing.SignatureExpired, Attachment.DoesNotExist, ValueError) as exc:
        raise Http404 from exc
    from members.api.viewsets.attachment_viewsets import AttachmentViewSet

    view = AttachmentViewSet()
    view.request = request
    view.action = "retrieve"
    view.kwargs = {"pk": pk}
    if not view.get_queryset().filter(pk=pk).exists():
        raise Http404
    return private_file_response(attachment.file, filename=attachment.name)


def deny_direct_attachments(request):
    raise Http404
