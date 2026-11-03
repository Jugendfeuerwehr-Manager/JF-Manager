from rest_framework import serializers

from membership.models import AnnualReport, StatisticsProfile


class StatisticsProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatisticsProfile
        fields = ["id", "department", "djf_org_id", "org_kind", "founded_on", "include_status_categories"]
        read_only_fields = ["id"]

    def validate_include_status_categories(self, value):
        allowed = {"trial", "active", "passive"}
        if not isinstance(value, list) or not set(value) <= allowed or not value:
            raise serializers.ValidationError("Erlaubt sind Probezeit, Aktiv und Passiv.")
        return sorted(set(value))


class AnnualReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnnualReport
        fields = ["id", "department", "year", "reference_date", "state", "finalized_at", "updated_at"]
        read_only_fields = fields


class ReportQuerySerializer(serializers.Serializer):
    department = serializers.IntegerField()
    year = serializers.IntegerField(min_value=2000, max_value=2100)


class CountsSerializer(serializers.Serializer):
    m = serializers.IntegerField(min_value=0, max_value=9999, required=False, default=0)
    w = serializers.IntegerField(min_value=0, max_value=9999, required=False, default=0)
    d = serializers.IntegerField(min_value=0, max_value=9999, required=False, default=0)


class ActivitySerializer(serializers.Serializer):
    label = serializers.CharField(max_length=200)
    value = serializers.IntegerField(min_value=0, max_value=99999)


class ManualSerializer(ReportQuerySerializer):
    supervisors = CountsSerializer(required=False)
    activities = ActivitySerializer(many=True, required=False, default=list)

    def validate(self, attrs):
        supervisors = attrs.get("supervisors")
        if supervisors is not None:
            supervisors["total"] = supervisors["m"] + supervisors["w"] + supervisors["d"]
        return attrs
