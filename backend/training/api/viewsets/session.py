"""ViewSet for TrainingSession."""

import datetime

from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from departments.mixins import DepartmentScopeViewSetMixin
from training.api.filters import TrainingSessionFilter
from training.api.permissions import CanManageTraining
from training.api.serializers import (
    TrainingSessionCreateSerializer,
    TrainingSessionDetailSerializer,
    TrainingSessionHandoutSerializer,
    TrainingSessionListSerializer,
)
from training.models import TrainingSession


class TrainingSessionViewSet(DepartmentScopeViewSetMixin, viewsets.ModelViewSet):
    """
    CRUD for training sessions + handout + generate_series actions.
    """

    authentication_classes = [JWTAuthentication, TokenAuthentication, SessionAuthentication]
    permission_classes = [CanManageTraining]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = TrainingSessionFilter
    ordering_fields = ["date", "start_time", "title"]
    ordering = ["date", "start_time"]
    queryset = TrainingSession.objects.all()  # required by mixin; overridden in get_queryset

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
        )
        self.queryset = qs
        return super().get_queryset()

    def _to_aware_datetime(self, date_value, time_value):
        dt = datetime.datetime.combine(date_value, time_value)
        if timezone.is_naive(dt):
            return timezone.make_aware(dt, timezone.get_current_timezone())
        return dt

    def _sync_linked_servicebook_entry(self, session):
        from servicebook.models import Service

        start = self._to_aware_datetime(session.date, session.start_time)
        end = self._to_aware_datetime(session.date, session.end_time)

        service, _ = Service.objects.get_or_create(
            training_session=session,
            defaults={
                "start": start,
                "end": end,
                "topic": session.title,
                "place": session.location,
                "description": session.description,
                "department": session.department,
            },
        )
        service.start = start
        service.end = end
        service.topic = session.title
        service.place = session.location
        service.description = session.description
        service.department = session.department
        service.save(
            update_fields=[
                "start",
                "end",
                "topic",
                "place",
                "description",
                "department",
            ]
        )

    def perform_create(self, serializer):
        session = serializer.save()
        self._sync_linked_servicebook_entry(session)

    def perform_update(self, serializer):
        session = serializer.save()
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

            if is_future_service and should_delete_linked_service:
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

    @action(detail=True, methods=["get"])
    def handout(self, request, pk=None):
        """
        GET /api/v1/training/sessions/{id}/handout/
        Returns full session data optimised for the trainer handout view.
        """
        session = self.get_object()
        serializer = self.get_serializer(session)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def generate_series(self, request, pk=None):
        """
        POST /api/v1/training/sessions/{id}/generate_series/
        Creates child sessions from the recurrence_rule on this session.
        Idempotent: deletes existing children before regenerating.
        """
        parent = self.get_object()
        if not parent.recurrence_rule:
            return Response(
                {"detail": "Diese Einheit hat keine Wiederholungsregel."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rule = parent.recurrence_rule
        frequency = rule.get("frequency", "WEEKLY")
        end_date_str = rule.get("end_date")
        if not end_date_str:
            return Response(
                {"detail": "recurrence_rule benötigt ein end_date."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            end_date = datetime.date.fromisoformat(end_date_str)
        except ValueError:
            return Response(
                {"detail": "Ungültiges end_date Format (erwartet YYYY-MM-DD)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        delta_map = {
            "WEEKLY": datetime.timedelta(weeks=1),
            "BIWEEKLY": datetime.timedelta(weeks=2),
            "MONTHLY": None,  # handled separately
        }
        delta = delta_map.get(frequency)

        # Delete previous children
        parent.series_children.all().delete()

        current_date = parent.date
        created = []

        while True:
            # Advance to next occurrence
            if frequency == "MONTHLY":
                month = current_date.month + 1
                year = current_date.year + (month - 1) // 12
                month = ((month - 1) % 12) + 1
                try:
                    current_date = current_date.replace(year=year, month=month)
                except ValueError:
                    import calendar

                    last_day = calendar.monthrange(year, month)[1]
                    current_date = current_date.replace(year=year, month=month, day=last_day)
            else:
                current_date = current_date + delta

            if current_date > end_date:
                break

            child = TrainingSession.objects.create(
                title=parent.title,
                description=parent.description,
                date=current_date,
                start_time=parent.start_time,
                end_time=parent.end_time,
                location=parent.location,
                notes=parent.notes,
                series_parent=parent,
                department=parent.department,
                created_by=request.user if request.user.is_authenticated else None,
            )
            child.groups.set(parent.groups.all())
            self._sync_linked_servicebook_entry(child)
            created.append(child.pk)

        return Response(
            {"created": len(created), "session_ids": created},
            status=status.HTTP_201_CREATED,
        )
