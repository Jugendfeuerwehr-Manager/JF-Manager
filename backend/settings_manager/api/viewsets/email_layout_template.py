"""
Email Layout Template ViewSet

Manages the customisable HTML wrapper templates used to style member emails.
"""

import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from orders.models import EmailLayoutTemplate

from ..permissions import CanChangeSettings
from ..serializers.email_layout_template import (
    EmailLayoutTemplateSerializer,
    EmailLayoutTemplateUpdateSerializer,
)

logger = logging.getLogger(__name__)

_LAYOUT_META = [
    {"value": "general", "label": "Allgemeine Information"},
    {"value": "important", "label": "Wichtige Mitteilung"},
    {"value": "events", "label": "Veranstaltung / Termin"},
]


def _read_default_content(layout_type: str) -> str:
    """Return the raw HTML of the static fallback layout template file."""
    from django.template.loader import get_template

    try:
        tpl = get_template(f"email_layouts/{layout_type}.html")
        with open(tpl.origin.name) as fh:
            return fh.read()
    except Exception as exc:
        logger.warning("Could not read default layout template '%s': %s", layout_type, exc)
        return f"<!-- Default layout template '{layout_type}' not found -->"


def _build_response_data(layout_meta: dict, db_obj: EmailLayoutTemplate | None) -> dict:
    if db_obj:
        return {
            "layout_type": layout_meta["value"],
            "label": layout_meta["label"],
            "html_content": db_obj.html_content,
            "is_custom": True,
            "updated_at": db_obj.updated_at,
        }
    return {
        "layout_type": layout_meta["value"],
        "label": layout_meta["label"],
        "html_content": _read_default_content(layout_meta["value"]),
        "is_custom": False,
        "updated_at": None,
    }


class EmailLayoutTemplateViewSet(viewsets.ViewSet):
    """
    ViewSet for managing email layout (wrapper) templates.

    The three layout types (general / important / events) always appear in
    list/retrieve responses. If no custom DB record exists the default file
    content is returned. A PUT request creates or updates the DB override.
    A POST to /reset/ deletes the override and reverts to the default.
    """

    permission_classes = [IsAuthenticated, CanChangeSettings]

    @extend_schema(responses=EmailLayoutTemplateSerializer(many=True))
    def list(self, request):
        """Return all three layout templates (custom DB version or default)."""
        db_map = {obj.layout_type: obj for obj in EmailLayoutTemplate.objects.all()}
        results = [_build_response_data(m, db_map.get(m["value"])) for m in _LAYOUT_META]
        serializer = EmailLayoutTemplateSerializer(results, many=True)
        return Response(serializer.data)

    @extend_schema(responses=EmailLayoutTemplateSerializer)
    def retrieve(self, request, pk=None):
        """Return a single layout template. pk = layout_type string."""
        meta = next((m for m in _LAYOUT_META if m["value"] == pk), None)
        if meta is None:
            return Response({"detail": "Nicht gefunden."}, status=status.HTTP_404_NOT_FOUND)
        db_obj = EmailLayoutTemplate.objects.filter(layout_type=pk).first()
        serializer = EmailLayoutTemplateSerializer(_build_response_data(meta, db_obj))
        return Response(serializer.data)

    @extend_schema(request=EmailLayoutTemplateUpdateSerializer, responses=EmailLayoutTemplateSerializer)
    def update(self, request, pk=None):
        """Create or update the custom HTML for a layout template."""
        meta = next((m for m in _LAYOUT_META if m["value"] == pk), None)
        if meta is None:
            return Response({"detail": "Nicht gefunden."}, status=status.HTTP_404_NOT_FOUND)
        input_serializer = EmailLayoutTemplateUpdateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        obj, _ = EmailLayoutTemplate.objects.update_or_create(
            layout_type=pk,
            defaults={"html_content": input_serializer.validated_data["html_content"]},
        )
        serializer = EmailLayoutTemplateSerializer(_build_response_data(meta, obj))
        return Response(serializer.data)

    @extend_schema(responses=EmailLayoutTemplateSerializer)
    @action(detail=True, methods=["post"])
    def reset(self, request, pk=None):
        """Delete the custom override and revert to the default file template."""
        meta = next((m for m in _LAYOUT_META if m["value"] == pk), None)
        if meta is None:
            return Response({"detail": "Nicht gefunden."}, status=status.HTTP_404_NOT_FOUND)
        EmailLayoutTemplate.objects.filter(layout_type=pk).delete()
        data = _build_response_data(meta, None)
        serializer = EmailLayoutTemplateSerializer(data)
        return Response(serializer.data)
