"""Whole-exercise templates: save, browse, instantiate and delete."""

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from departments.models import Department
from members.models import Attachment
from training.api.permissions import can_manage_training_department
from training.api.serializers.session import TrainingSessionDetailSerializer
from training.api.serializers.template import (
    CopyToDateSerializer,
    TrainingTemplateBlockSerializer,
    TrainingTemplateDetailSerializer,
    TrainingTemplateSerializer,
)
from training.copying import copied_files, template_to_session
from training.models import TrainingMedia, TrainingTemplate, TrainingTemplateBlock


def manageable_department_ids(user):
    if user.is_superuser or user.has_perm("departments.can_access_all_departments"):
        candidates = Department.objects.values_list("pk", flat=True)
    else:
        candidates = user.department_roles.values_list("department_id", flat=True)
    return [pk for pk in set(candidates) if can_manage_training_department(user, pk)]


class CanManageTemplates(permissions.BasePermission):
    """Templates are planning material: only planners of the template department."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if getattr(view, "read_only", False) and request.method not in permissions.SAFE_METHODS:
            return False
        return user.is_superuser or bool(manageable_department_ids(user))

    def has_object_permission(self, request, view, obj):
        template = getattr(obj, "template", obj)
        return can_manage_training_department(request.user, template.department_id)


class TrainingTemplateViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [CanManageTemplates]
    queryset = TrainingTemplate.objects.none()

    def get_queryset(self):
        queryset = TrainingTemplate.objects.select_related("created_by").prefetch_related("groups", "blocks__groups")
        if not self.request.user.is_superuser:
            queryset = queryset.filter(department_id__in=manageable_department_ids(self.request.user))
        department = self.request.query_params.get("department")
        if department and department.isdigit():
            queryset = queryset.filter(department_id=int(department))
        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return TrainingTemplateDetailSerializer
        return TrainingTemplateSerializer

    @transaction.atomic
    def perform_destroy(self, instance):
        # Generic relations do not cascade; remove the template's own file records.
        block_type = ContentType.objects.get_for_model(TrainingTemplateBlock)
        ids = list(instance.blocks.values_list("pk", flat=True))
        Attachment.objects.filter(content_type=block_type, object_id__in=ids).delete()
        TrainingMedia.objects.filter(content_type=block_type, object_id__in=ids).delete()
        instance.delete()

    @action(detail=True, methods=["post"])
    def instantiate(self, request, pk=None):
        """Create an independent draft exercise from this template."""
        template = self.get_object()
        payload = CopyToDateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        with transaction.atomic(), copied_files() as files:
            session = template_to_session(
                template, payload.validated_data["date"], request.user, files, payload.validated_data.get("title", "")
            )
        data = TrainingSessionDetailSerializer(session, context=self.get_serializer_context()).data
        return Response(data, status=status.HTTP_201_CREATED)


class TrainingTemplateBlockViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only owner view; governs access to template images and attachments."""

    permission_classes = [CanManageTemplates]
    serializer_class = TrainingTemplateBlockSerializer
    queryset = TrainingTemplateBlock.objects.none()
    read_only = True

    def get_queryset(self):
        queryset = TrainingTemplateBlock.objects.select_related("template").prefetch_related("groups")
        if self.request.user.is_superuser:
            return queryset
        return queryset.filter(template__department_id__in=manageable_department_ids(self.request.user))
