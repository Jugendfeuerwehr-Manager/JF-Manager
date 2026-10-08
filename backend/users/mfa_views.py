"""Self-service MFA enrolment and recent re-authentication for session users."""

import json

from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from users import mfa, passkeys
from users.mfa_policy import mfa_required
from users.models import MFADevice, MFARecoveryCode, PasskeyCredential
from users.session_auth import SessionAuthentication
from users.step_up import RecentReauthentication


class MFAThrottle(UserRateThrottle):
    scope = "mfa"
    rate = "5/min"


class SessionUserView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]


def mfa_status(user):
    device = MFADevice.objects.filter(user=user).first()
    totp_enabled = bool(device and device.is_confirmed)
    keys = [passkeys.serialize(p) for p in PasskeyCredential.objects.filter(user=user)]
    return {
        "enabled": totp_enabled or bool(keys),
        "totp_enabled": totp_enabled,
        "setup_pending": bool(device and not device.is_confirmed),
        "passkeys": keys,
        "recovery_codes_remaining": MFARecoveryCode.objects.filter(user=user, used_at__isnull=True).count(),
        "required": mfa_required(user),
    }


def _first_factor_codes(user, had_mfa):
    """Recovery codes are issued with the first factor and kept afterwards."""
    return mfa.issue_recovery_codes(user) if not had_mfa else []


class MFAStatusView(SessionUserView):
    """GET /api/v1/auth/mfa/"""

    def get(self, request):
        return Response(mfa_status(request.user))


class MFASetupView(SessionUserView):
    """POST /api/v1/auth/mfa/setup/ — start (or restart) enrolment."""

    permission_classes = [IsAuthenticated, RecentReauthentication]

    def post(self, request):
        if mfa.has_totp(request.user):
            return Response(
                {"detail": "Die Authenticator-App ist bereits eingerichtet."}, status=status.HTTP_409_CONFLICT
            )
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
            had_mfa = mfa.has_mfa(request.user)
            MFADevice.objects.filter(pk=device.pk).update(confirmed_at=timezone.now())
            codes = _first_factor_codes(request.user, had_mfa)
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
            PasskeyCredential.objects.filter(user=request.user).delete()
            MFARecoveryCode.objects.filter(user=request.user).delete()
        return Response(mfa_status(request.user))


def _last_factor_conflict(user, removing):
    """Mandatory MFA keeps at least one factor; ``removing`` is 'totp' or a passkey id."""
    if not mfa_required(user):
        return None
    totp = mfa.has_totp(user) and removing != "totp"
    others = PasskeyCredential.objects.filter(user=user)
    if removing != "totp":
        others = others.exclude(pk=removing)
    if totp or others.exists():
        return None
    return Response(
        {
            "detail": "Der letzte zweite Faktor eines MFA-pflichtigen Kontos kann nicht entfernt werden.",
            "code": "mfa_last_factor",
        },
        status=status.HTTP_409_CONFLICT,
    )


class MFATotpRemoveView(SessionUserView):
    """POST /api/v1/auth/mfa/totp/remove/ — keep passkeys, drop the authenticator app."""

    permission_classes = [IsAuthenticated, RecentReauthentication]

    def post(self, request):
        conflict = _last_factor_conflict(request.user, "totp")
        if conflict is not None:
            return conflict
        with transaction.atomic():
            MFADevice.objects.filter(user=request.user).delete()
            if not mfa.has_mfa(request.user):
                MFARecoveryCode.objects.filter(user=request.user).delete()
        return Response(mfa_status(request.user))


class PasskeyRegisterBeginView(SessionUserView):
    """POST /api/v1/auth/mfa/passkeys/register/begin/ — options for navigator.credentials.create()."""

    permission_classes = [IsAuthenticated, RecentReauthentication]

    def post(self, request):
        if PasskeyCredential.objects.filter(user=request.user).count() >= PasskeyCredential.MAX_PER_USER:
            return Response(
                {"detail": f"Es sind höchstens {PasskeyCredential.MAX_PER_USER} Passkeys möglich."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(json.loads(passkeys.registration_options(request.session, request.user)))


class PasskeyRegisterSerializer(serializers.Serializer):
    credential = serializers.DictField()
    name = serializers.CharField(max_length=64, required=False, allow_blank=True)


class PasskeyRegisterFinishView(SessionUserView):
    """POST /api/v1/auth/mfa/passkeys/register/finish/ — store a verified passkey."""

    permission_classes = [IsAuthenticated, RecentReauthentication]
    throttle_classes = [MFAThrottle]

    def post(self, request):
        serializer = PasskeyRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        had_mfa = mfa.has_mfa(request.user)
        try:
            passkeys.register(
                request.session,
                request.user,
                serializer.validated_data["credential"],
                serializer.validated_data.get("name", ""),
            )
        except passkeys.PasskeyError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        codes = _first_factor_codes(request.user, had_mfa)
        mfa.mark_mfa_verified(request)
        return Response({**mfa_status(request.user), "recovery_codes": codes})


class PasskeyDeleteView(SessionUserView):
    """POST /api/v1/auth/mfa/passkeys/<id>/remove/"""

    permission_classes = [IsAuthenticated, RecentReauthentication]

    def post(self, request, pk):
        credential = PasskeyCredential.objects.filter(user=request.user, pk=pk).first()
        if credential is None:
            return Response({"detail": "Nicht gefunden."}, status=status.HTTP_404_NOT_FOUND)
        conflict = _last_factor_conflict(request.user, pk)
        if conflict is not None:
            return conflict
        with transaction.atomic():
            credential.delete()
            if not mfa.has_mfa(request.user):
                MFARecoveryCode.objects.filter(user=request.user).delete()
        return Response(mfa_status(request.user))


class ReauthSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=4096, required=False, allow_blank=True, trim_whitespace=False)
    code = serializers.CharField(max_length=32, required=False, allow_blank=True)
    passkey = serializers.DictField(required=False)


class ReauthPasskeyOptionsView(SessionUserView):
    """POST /api/v1/auth/reauthenticate/passkey-options/ — challenge for a step-up."""

    throttle_classes = [MFAThrottle]

    def post(self, request):
        options = passkeys.authentication_options(request.session, request.user)
        if options is None:
            return Response(
                {"detail": "Für dieses Konto ist kein Passkey eingerichtet."}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(json.loads(options))


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
        if with_mfa and not self._second_factor(request, user, code, serializer.validated_data.get("passkey")):
            return Response({"detail": "Bestätigung fehlgeschlagen."}, status=status.HTTP_400_BAD_REQUEST)
        mfa.mark_reauthenticated(request)
        return Response({"reauthenticated": True})

    @staticmethod
    def _second_factor(request, user, code, passkey):
        if passkey:
            try:
                passkeys.authenticate(request.session, user, passkey)
            except passkeys.PasskeyError:
                return False
            return True
        return mfa.verify_second_factor(user, code)
