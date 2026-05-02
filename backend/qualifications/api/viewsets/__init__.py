"""
Enhanced ViewSets for Qualifications API.
Follows modular pattern from orders.api.viewsets with custom actions.
"""

from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import DjangoModelPermissions, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from jf_manager_backend.permissions import OrgWideWritePermission
from members.api_serializers import AttachmentSerializer
from members.models import Attachment
from qualifications.models import Qualification, QualificationType, SpecialTask, SpecialTaskType

from ..filters import QualificationFilter, SpecialTaskFilter
from ..serializers import (
    QualificationCreateSerializer,
    QualificationDetailSerializer,
    QualificationListSerializer,
    QualificationTypeListSerializer,
    QualificationTypeSerializer,
    QualificationUpdateSerializer,
    SpecialTaskCreateSerializer,
    SpecialTaskDetailSerializer,
    SpecialTaskListSerializer,
    SpecialTaskTypeSerializer,
    SpecialTaskUpdateSerializer,
)


class QualificationTypeViewSet(viewsets.ModelViewSet):
    """ViewSet for QualificationType"""

    queryset = QualificationType.objects.all().order_by("name")
    authentication_classes = [JWTAuthentication, TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated, DjangoModelPermissions, OrgWideWritePermission]
    filterset_fields = ["expires"]
    search_fields = ["name", "description"]
    ordering_fields = ["name"]

    def get_serializer_class(self):
        if self.action == "list":
            return QualificationTypeListSerializer
        return QualificationTypeSerializer


class QualificationViewSet(viewsets.ModelViewSet):
    """ViewSet for Qualifications with custom actions"""

    queryset = Qualification.objects.select_related("member", "user", "type").prefetch_related("attachments")
    authentication_classes = [JWTAuthentication, TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    filterset_class = QualificationFilter
    search_fields = [
        "member__first_name",
        "member__last_name",
        "user__first_name",
        "user__last_name",
        "type__name",
        "issued_by",
    ]
    ordering_fields = ["date_acquired", "date_expires"]
    ordering = ["-date_acquired"]

    def get_queryset(self):
        """Filter based on permissions"""
        user = self.request.user
        queryset = super().get_queryset()

        # Admin or staff can see all
        if user.has_perm("qualifications.view_all_qualifications"):
            return queryset

        # Regular users see only their own qualifications (linked via user FK)
        return queryset.filter(Q(user=user))

    def get_serializer_class(self):
        if self.action == "list":
            return QualificationListSerializer
        elif self.action == "create":
            return QualificationCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return QualificationUpdateSerializer
        return QualificationDetailSerializer

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """
        GET /api/v1/qualifications/statistics/

        Returns dashboard statistics
        """
        user = request.user

        # Filter based on permissions
        if user.has_perm("qualifications.view_all_qualifications"):
            qualifications_qs = Qualification.objects.all()
            special_tasks_qs = SpecialTask.objects.all()
        else:
            qualifications_qs = Qualification.objects.filter(Q(user=user))
            special_tasks_qs = SpecialTask.objects.filter(Q(user=user))

        today = date.today()
        soon_threshold = today + timedelta(days=30)

        # Calculate statistics
        expired = qualifications_qs.filter(date_expires__lt=today)
        expiring = qualifications_qs.filter(date_expires__gte=today, date_expires__lte=soon_threshold)
        active_tasks = special_tasks_qs.filter(Q(end_date__isnull=True) | Q(end_date__gt=today))
        completed_tasks = special_tasks_qs.filter(end_date__lte=today)

        # Recent and expiring lists
        recent = qualifications_qs.select_related("member", "user", "type").order_by("-date_acquired")[:5]
        expiring_list = expiring.select_related("member", "user", "type").order_by("date_expires")[:10]
        active_tasks_list = active_tasks.select_related("member", "user", "task").order_by("-start_date")[:10]

        return Response(
            {
                "total_qualifications": qualifications_qs.count(),
                "expired_qualifications": expired.count(),
                "expiring_qualifications": expiring.count(),
                "active_special_tasks": active_tasks.count(),
                "completed_special_tasks": completed_tasks.count(),
                "recent_qualifications": QualificationListSerializer(recent, many=True).data,
                "expiring_qualifications_list": QualificationListSerializer(expiring_list, many=True).data,
                "active_special_tasks_list": SpecialTaskListSerializer(active_tasks_list, many=True).data,
            }
        )

    @action(detail=False, methods=["post"])
    def calculate_expiry(self, request):
        """
        POST /api/v1/qualifications/calculate-expiry/

        Body: {
            "type_id": 1,
            "date_acquired": "2025-10-17"
        }

        Returns: {
            "date_expires": "2027-10-17" or null
        }
        """
        type_id = request.data.get("type_id")
        date_acquired_str = request.data.get("date_acquired")

        if not type_id or not date_acquired_str:
            return Response({"error": "type_id and date_acquired are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            qual_type = QualificationType.objects.get(id=type_id)
            date_acquired = date.fromisoformat(date_acquired_str)
        except (QualificationType.DoesNotExist, ValueError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if qual_type.expires and qual_type.validity_period:
            date_expires = date_acquired + relativedelta(months=qual_type.validity_period)
            return Response({"date_expires": date_expires.isoformat()})

        return Response({"date_expires": None})

    @action(detail=True, methods=["get", "post"], url_path="attachments", parser_classes=[MultiPartParser, FormParser])
    def attachments(self, request, pk=None):
        """
        GET: List attachments for a qualification
        POST: Upload an attachment for a qualification
        """
        qualification = self.get_object()

        if request.method == "GET":
            # List attachments
            attachments = qualification.attachments.all().order_by("-uploaded_at")
            serializer = AttachmentSerializer(attachments, many=True, context={"request": request})
            return Response(serializer.data)

        elif request.method == "POST":
            # Upload attachment
            if not request.user.has_perm("qualifications.change_qualification"):
                return Response({"detail": "Keine Berechtigung zum Bearbeiten."}, status=status.HTTP_403_FORBIDDEN)

            file_obj = request.FILES.get("file")
            name = request.data.get("name") or (file_obj.name if file_obj else None)
            description = request.data.get("description", "")

            if not file_obj or not name:
                return Response({"detail": "Datei und Name sind erforderlich."}, status=status.HTTP_400_BAD_REQUEST)

            attachment = Attachment.objects.create(
                content_object=qualification,
                file=file_obj,
                name=name,
                description=description,
                uploaded_by=request.user,
            )

            serializer = AttachmentSerializer(attachment, context={"request": request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path="attachments/(?P<attachment_id>[^/.]+)")
    def delete_attachment(self, request, pk=None, attachment_id=None):
        """Delete an attachment from a qualification."""
        qualification = self.get_object()

        if not request.user.has_perm("qualifications.change_qualification"):
            return Response({"detail": "Keine Berechtigung zum Löschen."}, status=status.HTTP_403_FORBIDDEN)

        attachment = get_object_or_404(qualification.attachments, pk=attachment_id)
        attachment.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class SpecialTaskTypeViewSet(viewsets.ModelViewSet):
    """ViewSet for SpecialTaskType"""

    queryset = SpecialTaskType.objects.all().order_by("name")
    serializer_class = SpecialTaskTypeSerializer
    authentication_classes = [JWTAuthentication, TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated, DjangoModelPermissions, OrgWideWritePermission]
    search_fields = ["name", "description"]
    ordering_fields = ["name"]


class SpecialTaskViewSet(viewsets.ModelViewSet):
    """ViewSet for Special Tasks with custom actions"""

    queryset = SpecialTask.objects.select_related("member", "user", "task").prefetch_related("attachments")
    authentication_classes = [JWTAuthentication, TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    filterset_class = SpecialTaskFilter
    search_fields = ["member__first_name", "member__last_name", "user__first_name", "user__last_name", "task__name"]
    ordering_fields = ["start_date", "end_date"]
    ordering = ["-start_date"]

    def get_queryset(self):
        """Filter based on permissions"""
        user = self.request.user
        queryset = super().get_queryset()

        if user.has_perm("qualifications.view_all_specialtasks"):
            return queryset

        return queryset.filter(Q(user=user) | Q(member__user=user))

    def get_serializer_class(self):
        if self.action == "list":
            return SpecialTaskListSerializer
        elif self.action == "create":
            return SpecialTaskCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return SpecialTaskUpdateSerializer
        return SpecialTaskDetailSerializer

    @action(detail=True, methods=["post"])
    def end_task(self, request, pk=None):
        """
        POST /api/v1/specialtasks/{id}/end-task/

        Sets end_date to today
        """
        task = self.get_object()

        if task.end_date and task.end_date <= date.today():
            return Response({"error": "Task is already ended"}, status=status.HTTP_400_BAD_REQUEST)

        task.end_date = date.today()
        task.save()

        serializer = self.get_serializer(task)
        return Response(serializer.data)

    @action(detail=True, methods=["get", "post"], url_path="attachments", parser_classes=[MultiPartParser, FormParser])
    def attachments(self, request, pk=None):
        """
        GET: List attachments for a special task
        POST: Upload an attachment for a special task
        """
        task = self.get_object()

        if request.method == "GET":
            # List attachments
            attachments = task.attachments.all().order_by("-uploaded_at")
            serializer = AttachmentSerializer(attachments, many=True, context={"request": request})
            return Response(serializer.data)

        elif request.method == "POST":
            # Upload attachment
            if not request.user.has_perm("qualifications.change_specialtask"):
                return Response({"detail": "Keine Berechtigung zum Bearbeiten."}, status=status.HTTP_403_FORBIDDEN)

            file_obj = request.FILES.get("file")
            name = request.data.get("name") or (file_obj.name if file_obj else None)
            description = request.data.get("description", "")

            if not file_obj or not name:
                return Response({"detail": "Datei und Name sind erforderlich."}, status=status.HTTP_400_BAD_REQUEST)

            attachment = Attachment.objects.create(
                content_object=task, file=file_obj, name=name, description=description, uploaded_by=request.user
            )

            serializer = AttachmentSerializer(attachment, context={"request": request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path="attachments/(?P<attachment_id>[^/.]+)")
    def delete_attachment(self, request, pk=None, attachment_id=None):
        """Delete an attachment from a special task."""
        task = self.get_object()

        if not request.user.has_perm("qualifications.change_specialtask"):
            return Response({"detail": "Keine Berechtigung zum Löschen."}, status=status.HTTP_403_FORBIDDEN)

        attachment = get_object_or_404(task.attachments, pk=attachment_id)
        attachment.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
