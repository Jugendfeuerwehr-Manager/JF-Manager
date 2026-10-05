"""Self-service MFA enrolment and recent re-authentication for session users."""

from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from users import mfa
from users.mfa_policy import mfa_required
from users.models import MFADevice, MFARecoveryCode


class MFAThrottle(UserRateThrottle):
    scope = "mfa"
    rate = "5/min"


class RecentReauthentication(BasePermission):
    """Security changes need a confirmation that is at most five minutes old."""

    message = "Bitte bestätigen Sie die Änderung erneut mit Ihren Anmeldedaten."
    code = "reauthentication_required"

    def has_permission(self, request, view):
        return mfa.recently_reauthenticated(request)


class SessionUserView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]


def mfa_status(user):
    device = MFADevice.objects.filter(user=user).first()
    return {
        "enabled": bool(device and device.is_confirmed),
        "setup_pending": bool(device and not device.is_confirmed),
        "recovery_codes_remaining": MFARecoveryCode.objects.filter(user=user, used_at__isnull=True).count(),
        "required": mfa_required(user),
    }


class MFAStatusView(SessionUserView):
    """GET /api/v1/auth/mfa/"""

    def get(self, request):
        return Response(mfa_status(request.user))


class MFASetupView(SessionUserView):
    """POST /api/v1/auth/mfa/setup/ — start (or restart) enrolment."""

    permission_classes = [IsAuthenticated, RecentReauthentication]

    def post(self, request):
        if mfa.has_mfa(request.user):
            return Response({"detail": "MFA ist bereits eingerichtet."}, status=status.HTTP_409_CONFLICT)
        secret = mfa.generate_secret()
        MFADevice.objects.update_or_create(
            user=request.user, defaults={"secret": secret, "confirmed_at": None, "last_used_step": 0}
        )
        return Response({"secret": secret, "otpauth_uri": mfa.provisioning_uri(secret, request.user.get_username())})


class CodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=32)


class MFAConfirmView(SessionUserView):
    """POST /api/v1/auth/mfa/confirm/ — prove the authenticator works."""

    throttle_classes = [MFAThrottle]

    def post(self, request):
        serializer = CodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device = MFADevice.objects.filter(user=request.user, confirmed_at__isnull=True).first()
        if device is None or not mfa.verify_totp(device.pk, serializer.validated_data["code"], require_confirmed=False):
            return Response({"detail": "Der Code ist ungültig oder abgelaufen."}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            MFADevice.objects.filter(pk=device.pk).update(confirmed_at=timezone.now())
            codes = mfa.issue_recovery_codes(request.user)
        mfa.mark_mfa_verified(request)
        return Response({**mfa_status(request.user), "recovery_codes": codes})


class MFARecoveryCodesView(SessionUserView):
    """POST /api/v1/auth/mfa/recovery-codes/ — replace all recovery codes."""

    permission_classes = [IsAuthenticated, RecentReauthentication]

    def post(self, request):
        if not mfa.has_mfa(request.user):
            return Response({"detail": "MFA ist nicht eingerichtet."}, status=status.HTTP_409_CONFLICT)
        return Response({"recovery_codes": mfa.issue_recovery_codes(request.user)})


class MFADisableView(SessionUserView):
    """POST /api/v1/auth/mfa/disable/"""

    permission_classes = [IsAuthenticated, RecentReauthentication]

    def post(self, request):
        if mfa_required(request.user):
            return Response(
                {"detail": "MFA ist für die Rollen dieses Kontos verpflichtend.", "code": "mfa_mandatory"},
                status=status.HTTP_409_CONFLICT,
            )
        with transaction.atomic():
            MFADevice.objects.filter(user=request.user).delete()
            MFARecoveryCode.objects.filter(user=request.user).delete()
        return Response(mfa_status(request.user))


class ReauthSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=4096, required=False, allow_blank=True, trim_whitespace=False)
    code = serializers.CharField(max_length=32, required=False, allow_blank=True)


class ReauthenticateView(SessionUserView):
    """POST /api/v1/auth/reauthenticate/ — confirm identity for five minutes."""

    throttle_classes = [MFAThrottle]

    def post(self, request):
        serializer = ReauthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        password = serializer.validated_data.get("password", "")
        code = serializer.validated_data.get("code", "")
        uses_password = user.auth_source != user.AuthSource.OIDC
        with_mfa = mfa.has_mfa(user)
        if not uses_password and not with_mfa:
            return Response(
                {"detail": "Bitte melden Sie sich erneut über SSO an.", "code": "sso_reauthentication_required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if uses_password:
            confirmed = authenticate(request._request, username=user.get_username(), password=password)
            if confirmed is None or confirmed.pk != user.pk:
                return Response({"detail": "Bestätigung fehlgeschlagen."}, status=status.HTTP_400_BAD_REQUEST)
        if with_mfa and not mfa.verify_second_factor(user, code):
            return Response({"detail": "Bestätigung fehlgeschlagen."}, status=status.HTTP_400_BAD_REQUEST)
        mfa.mark_reauthenticated(request)
        return Response({"reauthenticated": True})
