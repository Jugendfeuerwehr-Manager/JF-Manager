"""
Serializers for QualificationType model.
"""

from rest_framework import serializers

from qualifications.hierarchy import find_cycle
from qualifications.models import QualificationType


class QualificationTypeSerializer(serializers.ModelSerializer):
    """Full serializer for QualificationType.

    ``includes`` (write: ids) lists the types a holder of this type also satisfies (E18);
    ``includes_detail`` is the read-only id/name view of the same relation.
    """

    includes = serializers.PrimaryKeyRelatedField(many=True, queryset=QualificationType.objects.all(), required=False)
    includes_detail = serializers.SerializerMethodField()

    class Meta:
        model = QualificationType
        fields = ["id", "name", "expires", "validity_period", "description", "includes", "includes_detail"]

    def get_includes_detail(self, obj) -> list[dict]:
        return [{"id": t.pk, "name": t.name} for t in sorted(obj.includes.all(), key=lambda t: t.name)]

    def validate_includes(self, value):
        own_id = self.instance.pk if self.instance else None
        if own_id is not None and any(t.pk == own_id for t in value):
            raise serializers.ValidationError("Eine Qualifikation kann sich nicht selbst einschließen.")
        if own_id is not None and find_cycle(own_id, [t.pk for t in value]):
            raise serializers.ValidationError(
                "Zyklische Zuordnung: Eine der gewählten Qualifikationen schließt diese bereits ein."
            )
        return value


class QualificationTypeListSerializer(QualificationTypeSerializer):
    """Minimal serializer for dropdown/list views (plus the E18 relation for the management list)."""

    class Meta:
        model = QualificationType
        fields = ["id", "name", "expires", "includes", "includes_detail"]
