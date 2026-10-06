"""ViewSet for TrainingSession."""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response

from departments.mixins import DepartmentScopeViewSetMixin
from inventory.models import Item
from training.api.filters import TrainingSessionFilter
from training.api.permissions import CanManageTraining, can_manage_training_department, filter_training_queryset
from training.api.plan import PlanInputSerializer, advance_revision, lock_sessions, save_plan
from training.api.serializers import (
    TrainingSessionCreateSerializer,
    TrainingSessionDetailSerializer,
    TrainingSessionHandoutSerializer,
    TrainingSessionListSerializer,
)
from training.api.serializers.block import InstructorMiniSerializer
from training.api.serializers.template import CopyToDateSerializer, SaveAsTemplateSerializer, TrainingTemplateSerializer
from training.copying import copied_files, copy_session, eligible_instructors, session_to_template
from training.models import TrainingSession
from training.series import (
    PropagationInputSerializer,
    SeriesInputSerializer,
    generate_missing,
    generation_preview,
    lock_series,
    propagate,
    propagation_preview,
    series_root,
)
from training.workflow import service_is_documented, sync_linked_service

SERIES_ACTIONS = {"generate_series", "propagate_series"}


class TrainingSessionViewSet(DepartmentScopeViewSetMixin, viewsets.ModelViewSet):
    """
    CRUD for training sessions + handout + generate_series actions.
    """

    permission_classes = [CanManageTraining]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = TrainingSessionFilter
    ordering_fields = ["date", "start_time", "title"]
    ordering = ["date", "start_time"]
    queryset = TrainingSession.objects.all()  # required by mixin; overridden in get_queryset

    def dispatch(self, request, *args, **kwargs):
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            with transaction.atomic():
                return super().dispatch(request, *args, **kwargs)
        return super().dispatch(request, *args, **kwargs)

    def get_object(self):
        session = super().get_object()
        # Series actions lock the series root before any occurrence.
        if self.request.method in ("POST", "PUT", "PATCH", "DELETE") and self.action not in SERIES_ACTIONS:
            locked = lock_sessions([session.pk])
            if not locked:
                raise NotFound()
            session = locked[0]
            self.check_object_permissions(self.request, session)
        return session

    def get_queryset(self):
        qs = TrainingSession.objects.select_related(
            "created_by",
            "series_parent",
            "department",
            "servicebook_entry",
        ).prefetch_related(
            "groups",
            "blocks__groups",
            "blocks__library_block",
            "blocks__instructors",
            "blocks__materials",
        )
        self.queryset = qs
        return filter_training_queryset(self.request, super().get_queryset())

    _sync_linked_servicebook_entry = staticmethod(sync_linked_service)

    def perform_create(self, serializer):
        session = serializer.save()
        self._sync_linked_servicebook_entry(session)

    def perform_update(self, serializer):
        session = serializer.save()
        advance_revision(session)
        self._sync_linked_servicebook_entry(session)

    def destroy(self, request, *args, **kwargs):
        from servicebook.models import Service

        session = self.get_object()
        linked_service = Service.objects.filter(training_session=session).first()

        if linked_service is not None:
            should_delete_linked_service = request.query_params.get("delete_linked_service", "").lower() in {
                "1",
                "true",
                "yes",
            }
            is_future_service = linked_service.start >= timezone.now()

            if is_future_service and should_delete_linked_service and not service_is_documented(linked_service):
                linked_service.delete()
            else:
                linked_service.training_session = None
                linked_service.save(update_fields=["training_session"])

        return super().destroy(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.action == "list":
            return TrainingSessionListSerializer
        if self.action in ["create", "update", "partial_update"]:
            return TrainingSessionCreateSerializer
        if self.action == "handout":
            return TrainingSessionHandoutSerializer
        return TrainingSessionDetailSerializer

    @action(detail=True, methods=["get", "put"])
    def plan(self, request, pk=None):
        """Read/replace the full plan. Omitted existing blocks are removed."""
        session = self.get_object()
        if request.method == "GET":
            return Response(TrainingSessionDetailSerializer(session, context=self.get_serializer_context()).data)
        payload = PlanInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        if payload.validated_data["expected_revision"] != session.revision:
            return Response(
                {
                    "code": "plan_revision_conflict",
                    "detail": "Der Plan wurde inzwischen geändert. Lokalen Entwurf vergleichen.",
                    "current": TrainingSessionDetailSerializer(session, context=self.get_serializer_context()).data,
                },
                status=status.HTTP_409_CONFLICT,
            )
        session = save_plan(
            session, payload.validated_data, self.get_serializer_context(), self._sync_linked_servicebook_entry
        )
        return Response(TrainingSessionDetailSerializer(session, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["get"])
    def handout(self, request, pk=None):
        """
        GET /api/v1/training/sessions/{id}/handout/
        Returns full session data optimised for the trainer handout view.
        """
        session = self.get_object()
        serializer = self.get_serializer(session)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def series_preview(self, request, pk=None):
        """Complete, bounded preview of missing occurrences; nothing is changed."""
        session = self.get_object()
        payload = SeriesInputSerializer(data=request.query_params)
        payload.is_valid(raise_exception=True)
        root = series_root(session)
        children = list(root.series_children.order_by("pk"))
        return Response(generation_preview(root, children, payload.validated_data, request.user))

    @action(detail=True, methods=["post"])
    def generate_series(self, request, pk=None):
        """
        POST /api/v1/training/sessions/{id}/generate_series/
        Adds missing occurrences of the confirmed preview. Existing sessions,
        plans, services and attendances are never deleted or regenerated.
        """
        session = self.get_object()
        payload = SeriesInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        if not payload.validated_data.get("preview_token"):
            raise ValidationError({"preview_token": "Vorschau bestätigen, bevor Termine erzeugt werden."})
        root, children = lock_series(session)
        result, preview = generate_missing(root, children, payload.validated_data, request.user)
        if result is None:
            return Response(
                {
                    "code": "series_preview_changed",
                    "detail": "Die Serie wurde inzwischen geändert. Aktualisierte Vorschau prüfen.",
                    "preview": preview,
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(result, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def propagation_preview(self, request, pk=None):
        """'This and following': complete preview of the saved state; nothing is changed."""
        session = self.get_object()
        payload = PropagationInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        root = series_root(session)
        children = list(root.series_children.order_by("pk"))
        return Response(propagation_preview(session, root, children, payload.validated_data, request.user))

    @action(detail=True, methods=["post"])
    def propagate_series(self, request, pk=None):
        """Applies the confirmed preview; deviating dates only when explicitly listed."""
        session = self.get_object()
        payload = PropagationInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        if not payload.validated_data.get("preview_token"):
            raise ValidationError({"preview_token": "Vorschau bestätigen, bevor Folgetermine geändert werden."})
        root, children = lock_series(session)
        result, preview = propagate(session, root, children, payload.validated_data, request.user)
        if result is None:
            return Response(
                {
                    "code": "series_preview_changed",
                    "detail": "Serie oder Termine wurden inzwischen geändert. Aktualisierte Vorschau prüfen.",
                    "preview": preview,
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(result)

    @action(detail=True, methods=["post"])
    def save_as_template(self, request, pk=None):
        """Save the stored plan as an independent exercise template (own file copies)."""
        session = self.get_object()
        payload = SaveAsTemplateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        with copied_files() as files:
            template = session_to_template(session, request.user, files, payload.validated_data.get("title", ""))
        return Response(TrainingTemplateSerializer(template).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def copy(self, request, pk=None):
        """Independent draft copy on another date; not part of any series."""
        session = self.get_object()
        payload = CopyToDateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        title = payload.validated_data.get("title") or session.title
        with copied_files() as files:
            copy = copy_session(session, payload.validated_data["date"], request.user, files, title=title)
        return Response(
            TrainingSessionDetailSerializer(copy, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    def _planning_session(self):
        session = self.get_object()
        if not can_manage_training_department(self.request.user, session.department_id):
            raise PermissionDenied("Nur Planer dieser Übungsabteilung.")
        return session

    @action(detail=True, methods=["get"])
    def instructor_options(self, request, pk=None):
        """Minimal list: active accounts with a role in the exercise department."""
        session = self._planning_session()
        users = eligible_instructors(get_user_model().objects.all(), session.department_id).order_by(
            "last_name", "first_name", "username"
        )
        return Response(InstructorMiniSerializer(users[:500], many=True).data)

    @action(detail=True, methods=["get"])
    def material_options(self, request, pk=None):
        """Minimal item lookup (department items and shared items) for material needs."""
        session = self._planning_session()
        items = Item.objects.filter(Q(department_id=session.department_id) | Q(department__isnull=True))
        search = request.query_params.get("search", "").strip()
        if search:
            items = items.filter(name__icontains=search)
        items = items.prefetch_related("variants").order_by("name", "pk")[:30]
        return Response(
            [
                {
                    "id": item.pk,
                    "name": item.name or f"Artikel #{item.pk}",
                    "unit": item.base_unit,
                    "variants": [{"id": variant.pk, "label": str(variant)} for variant in item.variants.all()],
                }
                for item in items
            ]
        )
