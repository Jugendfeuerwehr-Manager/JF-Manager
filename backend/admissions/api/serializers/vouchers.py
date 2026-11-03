from rest_framework import serializers

from admissions.models import AdmissionVoucher
from admissions.services.vouchers import DEFAULT_VALIDITY_DAYS, MAX_VALIDITY_DAYS


class AdmissionVoucherSerializer(serializers.ModelSerializer):
    state = serializers.CharField(read_only=True)
    form_title = serializers.CharField(source="form.title", read_only=True)
    application = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = AdmissionVoucher
        fields = [
            "id",
            "form",
            "form_title",
            "department",
            "code_hint",
            "label",
            "prefill",
            "expires_at",
            "used_at",
            "revoked_at",
            "state",
            "application",
            "created_at",
        ]
        read_only_fields = fields


class AdmissionVoucherCreateSerializer(serializers.Serializer):
    form = serializers.IntegerField()
    label = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    vorname = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    nachname = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    valid_days = serializers.IntegerField(min_value=1, max_value=MAX_VALIDITY_DAYS, default=DEFAULT_VALIDITY_DAYS)


class PublicSubmitSerializer(serializers.Serializer):
    answers = serializers.DictField()
