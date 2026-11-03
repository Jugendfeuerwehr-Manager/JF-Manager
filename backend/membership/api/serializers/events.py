from rest_framework import serializers

from membership.models import MembershipEvent


class MembershipEventSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    exit_reason_label = serializers.CharField(source="get_exit_reason_display", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)
    from_status_name = serializers.CharField(source="from_status.name", read_only=True, default=None)
    to_status_name = serializers.CharField(source="to_status.name", read_only=True, default=None)

    class Meta:
        model = MembershipEvent
        fields = [
            "id",
            "member",
            "department",
            "department_name",
            "date",
            "kind",
            "kind_label",
            "exit_reason",
            "exit_reason_label",
            "from_status_name",
            "to_status_name",
            "note",
            "created_at",
        ]
        read_only_fields = ["id", "member", "department", "created_at"]


class MembershipEventCorrectionSerializer(MembershipEventSerializer):
    """Corrections keep the movement's direction: a join stays a join, an exit stays an exit."""

    def validate(self, attrs):
        kind = attrs.get("kind", self.instance.kind)
        reason = attrs.get("exit_reason", self.instance.exit_reason)
        if self._direction(kind) != self._direction(self.instance.kind):
            raise serializers.ValidationError({"kind": "Ein Zugang bleibt ein Zugang, ein Abgang ein Abgang."})
        if reason and kind != MembershipEvent.Kind.EXIT_OTHER:
            raise serializers.ValidationError({"exit_reason": "Ein Grund gehört nur zu „Abgang sonstige“."})
        return attrs

    @staticmethod
    def _direction(kind):
        if kind in MembershipEvent.JOIN_KINDS:
            return "join"
        if kind in MembershipEvent.EXIT_KINDS:
            return "exit"
        return kind
