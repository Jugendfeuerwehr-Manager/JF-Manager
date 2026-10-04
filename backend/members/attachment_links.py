from django.core import signing
from django.http import FileResponse, Http404
from django.urls import reverse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from members.api.serializers.list_serializers import can_write_list_department
from members.models import Attachment, MemberList

SALT = "jf-attachment-preview-v1"


def preview_url(attachment):
    token = signing.dumps([attachment.pk, attachment.file.name], salt=SALT)
    return reverse("attachment-preview", kwargs={"pk": attachment.pk, "token": token})


@api_view(["GET"])
@permission_classes([AllowAny])
def attachment_preview(request, pk, token):
    try:
        signed_id, file_name = signing.loads(token, salt=SALT, max_age=300)
        attachment = Attachment.objects.get(pk=pk)
        if signed_id != attachment.pk or not attachment.file or file_name != attachment.file.name:
            raise Http404
    except (signing.BadSignature, signing.SignatureExpired, Attachment.DoesNotExist, ValueError) as exc:
        raise Http404 from exc
    owner = attachment.content_object
    if owner is None:
        raise Http404
    if isinstance(owner, MemberList) and (
        not request.user.is_authenticated
        or (owner.department_id is None and not request.user.is_superuser)
        or (owner.department_id is not None and not can_write_list_department(request.user, owner.department, "view"))
    ):
        raise Http404
    response = FileResponse(attachment.file.open("rb"), content_type=attachment.mime_type or "application/octet-stream")
    response["Cache-Control"] = "private, no-store"
    response["Referrer-Policy"] = "no-referrer"
    response["Content-Security-Policy"] = "sandbox"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def deny_direct_attachments(request):
    raise Http404
