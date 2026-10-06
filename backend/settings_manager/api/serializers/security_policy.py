from rest_framework import serializers

from settings_manager.runtime_policy import POLICY_FIELDS


class SecurityPolicySerializer(serializers.Serializer):
    session_idle_timeout_seconds = serializers.IntegerField(min_value=300, max_value=90 * 86400)
    session_max_age_seconds = serializers.IntegerField(min_value=3600, max_value=365 * 86400)
    privileged_session_idle_timeout_seconds = serializers.IntegerField(min_value=300, max_value=86400)
    privileged_session_max_age_seconds = serializers.IntegerField(min_value=3600, max_value=7 * 86400)
    fields = serializers.DictField(read_only=True)

    def validate(self, attrs):
        for prefix in ("", "privileged_"):
            if attrs[f"{prefix}session_idle_timeout_seconds"] > attrs[f"{prefix}session_max_age_seconds"]:
                raise serializers.ValidationError(
                    {
                        f"{prefix}session_idle_timeout_seconds": "Die Inaktivitätsdauer darf die Höchstdauer nicht überschreiten."
                    }
                )
        return attrs

    def to_internal_value(self, data):
        unknown = set(data) - POLICY_FIELDS.keys()
        if unknown:
            raise serializers.ValidationError({name: "Unbekanntes oder schreibgeschütztes Feld." for name in unknown})
        return super().to_internal_value(data)
