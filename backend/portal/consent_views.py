"""Parents grant and withdraw consents for each child in the portal (DSGVO Art. 7)."""

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from participation.throttles import PortalWriteThrottle
from privacy.models import ConsentRecord
from privacy.services import consent as consent_service

from .people import portal_children
from .permissions import PortalAccountRequired


def _entry(record):
    if record is None:
        return None
    by = record.recorded_by
    return {
        "status": record.status,
        "recorded_at": record.recorded_at,
        "recorded_by_name": (by.get_full_name() or by.username) if by else "",
        "source": record.source,
        "text_version": record.text_version,
    }


def consents_payload(user):
    kinds = list(consent_service.portal_kinds())
    people = []
    for child in portal_children(user).order_by("name", "lastname"):
        current = consent_service.current_consents(child)
        people.append(
            {
                "member_id": child.pk,
                "name": f"{child.name} {child.lastname}".strip(),
                "consents": {kind.slug: _entry(current.get(kind.slug)) for kind in kinds},
            }
        )
    return {
        "kinds": [
            {"slug": k.slug, "label": k.label, "description": k.description, "version": k.version} for k in kinds
        ],
        "people": people,
    }


class _ChangeSerializer(serializers.Serializer):
    member = serializers.IntegerField()
    kind = serializers.SlugField()
    status = serializers.ChoiceField(choices=ConsentRecord.Status.choices)


class PortalConsentsView(APIView):
    """GET/POST /portal/consents/ — consents per child; every change is a new, logged row."""

    portal_access = True
    permission_classes = [PortalAccountRequired]
    throttle_classes = [PortalWriteThrottle]

    @extend_schema(summary="Consents of the own children")
    def get(self, request):
        return Response(consents_payload(request.user))

    @extend_schema(summary="Grant or withdraw a consent for a child", request=_ChangeSerializer)
    def post(self, request):
        data = _ChangeSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        child = portal_children(request.user).filter(pk=data.validated_data["member"]).first()
        kind = consent_service.portal_kinds().filter(slug=data.validated_data["kind"]).first()
        if child is None or kind is None:
            raise NotFound()  # foreign ids look like missing ones
        current = consent_service.current_consents(child).get(kind.slug)
        if current is not None and current.status == data.validated_data["status"]:
            return Response(consents_payload(request.user))  # nothing changes, nothing to log
        with transaction.atomic():
            consent_service.change_from_portal(child, kind, data.validated_data["status"], user=request.user)
        return Response(consents_payload(request.user), status=status.HTTP_201_CREATED)
