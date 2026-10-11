"""Saved list filters per user and department (UX-02.3)."""

import re

from rest_framework import serializers, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from departments.models import Department
from portal.permissions import StaffAccountRequired
from users.models import ListPreference

_SORT_FIELD = re.compile(r"^[a-z_]{1,40}$")


def _optional_id(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise serializers.ValidationError("Ungültige Kennung.")
    return value


def _gender(value):
    if value in (None, ""):
        return ""
    if not isinstance(value, str) or len(value) > 10:
        raise serializers.ValidationError("Ungültiger Wert.")
    return value


def _rows(value):
    if value not in (10, 20, 50, 100):
        raise serializers.ValidationError("Erlaubt sind 10, 20, 50 oder 100 Zeilen.")
    return value


def _sort_field(value):
    if not isinstance(value, str) or not _SORT_FIELD.match(value):
        raise serializers.ValidationError("Ungültiges Sortierfeld.")
    return value


def _sort_order(value):
    if value not in (1, -1):
        raise serializers.ValidationError("Sortierung ist 1 oder -1.")
    return value


# Allowed keys per view. Search texts are deliberately absent: they may contain names.
VIEW_FIELDS = {
    "members": {
        "status": _optional_id,
        "group": _optional_id,
        "gender": _gender,
        "rows": _rows,
        "sortField": _sort_field,
        "sortOrder": _sort_order,
    },
}


class ListPreferenceSerializer(serializers.Serializer):
    view = serializers.ChoiceField(choices=sorted(VIEW_FIELDS))
    department = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    data = serializers.DictField()

    def validate_department(self, value):
        if value is not None and not Department.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Abteilung nicht gefunden.")
        return value

    def validate(self, attrs):
        fields = VIEW_FIELDS[attrs["view"]]
        unknown = sorted(set(attrs["data"]) - set(fields))
        if unknown:
            raise serializers.ValidationError({"data": f"Nicht speicherbar: {', '.join(unknown)}."})
        cleaned, errors = {}, {}
        for key, value in attrs["data"].items():
            try:
                cleaned[key] = fields[key](value)
            except serializers.ValidationError as exc:
                errors[key] = exc.detail
        if errors:
            raise serializers.ValidationError({"data": errors})
        attrs["data"] = cleaned
        return attrs


class ListPreferenceViewSet(viewsets.ViewSet):
    """Read and save the signed-in account's own list settings.

    Own layout data only, so no model or department permission applies; portal accounts stay
    excluded (StaffAccountRequired), which is why the default permission classes are replaced.
    """

    permission_classes = [IsAuthenticated, StaffAccountRequired]

    def _department(self, raw):
        if raw in (None, "", "null"):
            return None
        try:
            return int(raw)
        except (TypeError, ValueError) as exc:
            raise serializers.ValidationError({"department": "Ungültige Abteilung."}) from exc

    def list(self, request):
        view = request.query_params.get("view", "")
        if view not in VIEW_FIELDS:
            return Response({"view": "Unbekannte Ansicht."}, status=status.HTTP_400_BAD_REQUEST)
        department = self._department(request.query_params.get("department"))
        preference = ListPreference.objects.filter(user=request.user, view=view, department_id=department).first()
        return Response({"view": view, "department": department, "data": preference.data if preference else {}})

    def create(self, request):
        serializer = ListPreferenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        department = values.get("department")
        preference, _ = ListPreference.objects.update_or_create(
            user=request.user, view=values["view"], department_id=department, defaults={"data": values["data"]}
        )
        return Response({"view": preference.view, "department": department, "data": preference.data})
