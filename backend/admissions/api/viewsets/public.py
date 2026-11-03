"""Public endpoints for applicants. No account; a voucher code or a public form link opens a form.

The code travels in the ``X-Admission-Code`` header, never in the URL: URLs end up in proxy
and server logs (DSGVO). The QR code carries it in the URL fragment, which browsers do not send.
A public link is meant to be shared, so its slug may sit in the path.
"""

from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from admissions.api.serializers.vouchers import PublicSubmitSerializer
from admissions.api.throttles import AdmissionCodeThrottle
from admissions.services import submission
from admissions.services.vouchers import VoucherError
from users.session_views import SessionCsrfMixin

INVALID = {"detail": "Der Code ist ungültig, abgelaufen oder wurde bereits verwendet.", "code": "invalid_code"}
UNAVAILABLE = {"detail": "Dieses Formular ist nicht (mehr) öffentlich.", "code": "form_unavailable"}


def _created(application, seal):
    return Response(
        {
            "applicant_name": application.applicant_name,
            "submitted_at": application.submitted_at,
            "seal": {"public_id": seal.public_id, "seal_hash": seal.seal_hash},
        },
        status=status.HTTP_201_CREATED,
    )


def _code(request):
    return request.headers.get("X-Admission-Code", "")


class PublicAdmissionViewSet(SessionCsrfMixin, viewsets.ViewSet):
    # SessionCsrfMixin: AllowAny without authentication; applicants have no account.
    throttle_classes = [AdmissionCodeThrottle]

    @extend_schema(summary="The published form for a voucher code (code in X-Admission-Code)")
    def list(self, request):
        try:
            voucher, version = submission.form_for_code(_code(request))
        except VoucherError:
            return Response(INVALID, status=status.HTTP_404_NOT_FOUND)
        return Response(
            {
                "department": voucher.department.name,
                "title": version.title,
                "intro": version.intro,
                "signature_mode": version.signature_mode,
                "decision_body": voucher.form.decision_body,
                "version": version.version,
                "schema": version.schema,
                "prefill": voucher.prefill,
                "expires_at": voucher.expires_at,
            }
        )

    @extend_schema(summary="Submit the application (code in X-Admission-Code)", request=PublicSubmitSerializer)
    def create(self, request):
        data = PublicSubmitSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            application, seal = submission.submit(_code(request), data.validated_data["answers"])
        except VoucherError:
            return Response(INVALID, status=status.HTTP_404_NOT_FOUND)
        return _created(application, seal)

    @extend_schema(summary="A public form (GET) or submit to it (POST) with the chosen department")
    @action(detail=False, methods=["get", "post"], url_path=r"form/(?P<slug>[a-z0-9-]{1,80})")
    def form(self, request, slug=None):
        try:
            form, version = submission.public_form(slug)
        except VoucherError:
            return Response(UNAVAILABLE, status=status.HTTP_404_NOT_FOUND)
        if request.method == "GET":
            return Response(
                {
                    "department": form.department.name if form.department else "",
                    "departments": [{"id": d.pk, "name": d.name} for d in form.selectable_departments()],
                    "title": version.title,
                    "intro": version.intro,
                    "signature_mode": version.signature_mode,
                    "decision_body": form.decision_body,
                    "version": version.version,
                    "schema": version.schema,
                    "prefill": {},
                    "expires_at": None,
                }
            )
        data = PublicSubmitSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        if data.validated_data["website"]:
            # Honeypot filled: a bot. Same answer as an invalid choice, nothing stored.
            return Response({"department": ["Bitte eine der angebotenen Abteilungen wählen."]}, status=400)
        application, seal = submission.submit_public(
            slug, data.validated_data["answers"], data.validated_data["department"]
        )
        return _created(application, seal)

    @extend_schema(summary="Check a seal by its public id; reveals no personal data")
    @action(detail=False, methods=["get"], url_path=r"verify/(?P<public_id>[A-Za-z0-9_-]+)")
    def verify(self, request, public_id=None):
        from admissions.services.verification import verify_public

        result = verify_public(public_id) if len(public_id) <= 16 else None
        if result is None:
            return Response({"valid": False, "detail": "Unbekanntes Siegel."}, status=status.HTTP_404_NOT_FOUND)
        return Response(result)
