from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import DjangoModelPermissions, IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import Qualification, QualificationType, SpecialTask, SpecialTaskType
from .serializers import (
    QualificationSerializer,
    QualificationTypeSerializer,
    SpecialTaskSerializer,
    SpecialTaskTypeSerializer,
)


class QualificationTypeViewSet(viewsets.ModelViewSet):
    """ViewSet für Qualifikationstypen"""

    queryset = QualificationType.objects.all()
    serializer_class = QualificationTypeSerializer
    authentication_classes = [JWTAuthentication, TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    filterset_fields = ["expires"]
    search_fields = ["name", "description"]
    ordering_fields = ["name"]
    ordering = ["name"]


class QualificationViewSet(viewsets.ModelViewSet):
    """ViewSet für Qualifikationen"""

    queryset = Qualification.objects.select_related("member", "user", "type")
    serializer_class = QualificationSerializer
    authentication_classes = [JWTAuthentication, TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    filterset_fields = ["member", "user", "type"]
    search_fields = ["member__first_name", "member__last_name", "user__first_name", "user__last_name", "type__name"]
    ordering_fields = ["date_acquired", "date_expires", "member__last_name"]
    ordering = ["-date_acquired"]


class SpecialTaskTypeViewSet(viewsets.ModelViewSet):
    """ViewSet für Sonderaufgaben-Typen"""

    queryset = SpecialTaskType.objects.all()
    serializer_class = SpecialTaskTypeSerializer
    authentication_classes = [JWTAuthentication, TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    filterset_fields = []
    search_fields = ["name", "description"]
    ordering_fields = ["name"]
    ordering = ["name"]


class SpecialTaskViewSet(viewsets.ModelViewSet):
    """ViewSet für Sonderaufgaben"""

    queryset = SpecialTask.objects.select_related("member", "user", "task")
    serializer_class = SpecialTaskSerializer
    authentication_classes = [JWTAuthentication, TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    filterset_fields = ["member", "user", "task"]
    search_fields = ["member__first_name", "member__last_name", "user__first_name", "user__last_name", "task__name"]
    ordering_fields = ["start_date", "end_date", "member__last_name"]
    ordering = ["-start_date"]
