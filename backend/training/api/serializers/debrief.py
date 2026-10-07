"""Follow-up of a held exercise (TRAIN-04.3)."""

from rest_framework import serializers

from training.models import TrainingDebrief


class TrainingDebriefSerializer(serializers.ModelSerializer):
    actual_minutes = serializers.IntegerField(read_only=True)
    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = TrainingDebrief
        fields = [
            "actual_start",
            "actual_end",
            "actual_minutes",
            "reflection",
            "improvements",
            "revision",
            "updated_by_name",
            "updated_at",
        ]

    def get_updated_by_name(self, obj):
        user = obj.updated_by
        return (user.get_full_name() or user.username) if user else None


class DebriefInputSerializer(serializers.Serializer):
    expected_revision = serializers.IntegerField(min_value=0)
    actual_start = serializers.TimeField(allow_null=True, required=False, default=None)
    actual_end = serializers.TimeField(allow_null=True, required=False, default=None)
    reflection = serializers.CharField(allow_blank=True, required=False, default="", max_length=5000)
    improvements = serializers.CharField(allow_blank=True, required=False, default="", max_length=5000)
    complete = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        start, end = attrs["actual_start"], attrs["actual_end"]
        if (start is None) != (end is None):
            raise serializers.ValidationError({"actual_end": "Tatsächlichen Beginn und Ende gemeinsam angeben."})
        if start is not None and end <= start:
            raise serializers.ValidationError({"actual_end": "Das tatsächliche Ende muss nach dem Beginn liegen."})
        return attrs
