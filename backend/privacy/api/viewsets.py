from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from privacy.api.permissions import PrivacySettingsPermission
from privacy.api.serializers import (
    ConsentCreateSerializer,
    ConsentRecordSerializer,
    LegalPageSerializer,
    LegalPageVersionSerializer,
    PublicLegalPageSerializer,
    PublishSerializer,
)
from privacy.api.subjects import resolve_subject
from privacy.models import ConsentRecord, LegalPage
from privacy.services import consent as consent_service
from privacy.services import legal


class LegalPageViewSet(viewsets.GenericViewSet):
    """Editor for imprint and privacy notice: draft, publish, version history."""

    permission_classes = [IsAuthenticated, PrivacySettingsPermission]
    serializer_class = LegalPageSerializer
    lookup_field = "kind"
    lookup_value_regex = "|".join(LegalPage.Kind.values)
    pagination_class = None

    def get_queryset(self):
        legal.ensure_pages()
        return LegalPage.objects.order_by("kind")

    def list(self, request):
        return Response(self.get_serializer(self.get_queryset(), many=True).data)

    def retrieve(self, request, kind=None):
        return Response(self.get_serializer(legal.get_page(kind)).data)

    def partial_update(self, request, kind=None):
        page = legal.get_page(kind)
        serializer = self.get_serializer(page, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        legal.save_draft(
            page,
            title=serializer.validated_data.get("draft_title", page.draft_title),
            body=serializer.validated_data.get("draft_body", page.draft_body),
            user=request.user,
        )
        return Response(self.get_serializer(page).data)

    @extend_schema(request=PublishSerializer, responses=LegalPageSerializer)
    @action(detail=True, methods=["post"])
    def publish(self, request, kind=None):
        data = PublishSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        page = legal.get_page(kind)
        try:
            legal.publish(page, user=request.user, change_note=data.validated_data["change_note"])
        except legal.LegalPageError as error:
            raise ValidationError({"detail": str(error)}) from error
        return Response(self.get_serializer(page).data, status=status.HTTP_201_CREATED)

    @extend_schema(responses=LegalPageVersionSerializer(many=True))
    @action(detail=True, methods=["get"])
    def versions(self, request, kind=None):
        page = legal.get_page(kind)
        return Response(LegalPageVersionSerializer(page.versions.select_related("published_by"), many=True).data)


class PublicLegalPageView(APIView):
    """Public: the published imprint or privacy notice (no login, also for portal accounts)."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses=PublicLegalPageSerializer)
    def get(self, request, kind):
        current = legal.published(kind)
        if current is None:
            raise NotFound("Dieser Rechtstext ist noch nicht veröffentlicht.")
        return Response(PublicLegalPageSerializer(current).data)


class ConsentRecordViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """Consents of one person (?member=, ?parent= or ?user=).

    Rights follow the person, not a separate model right: reading needs the
    read right on the member/parent in one of its departments, recording
    needs the change right there (accounts: user administration rights).
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ConsentRecordSerializer
    pagination_class = None

    def get_queryset(self):
        field, subject = resolve_subject(self.request, self.request.query_params, write=False)
        return ConsentRecord.objects.filter(**{field: subject}).select_related("recorded_by")

    @extend_schema(request=ConsentCreateSerializer, responses=ConsentRecordSerializer)
    def create(self, request, *args, **kwargs):
        data = ConsentCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        _, subject = resolve_subject(request, data.validated_data, write=True)
        record = consent_service.record_consent(
            subject,
            data.validated_data["kind"],
            data.validated_data["status"],
            source=ConsentRecord.Source.STAFF,
            text_version=data.validated_data["text_version"],
            recorded_by=request.user,
            note=data.validated_data["note"],
        )
        return Response(ConsentRecordSerializer(record).data, status=status.HTTP_201_CREATED)
