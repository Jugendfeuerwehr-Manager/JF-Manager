"""Step-up confirmation for actions that widen access or expose bulk data.

Ordinary sessions run for weeks; instead of short sessions, these actions need
a confirmation (password and, if set up, second factor) at most five minutes
old. Add the permissions after the authorization checks so that unauthorized
users get a plain 403 instead of a confirmation prompt.
"""

from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import ForcedAuthentication

from users import mfa

STEP_UP_MESSAGE = "Bitte bestätigen Sie die Änderung erneut mit Ihren Anmeldedaten."
STEP_UP_CODE = "reauthentication_required"


def require_step_up(request):
    # Tests may authenticate without a session; every real client has one.
    if isinstance(getattr(request, "successful_authenticator", None), ForcedAuthentication):
        return True
    if not mfa.recently_reauthenticated(request):
        # The code must reach the client so it can ask for confirmation.
        raise PermissionDenied({"detail": STEP_UP_MESSAGE, "code": STEP_UP_CODE})
    return True


class RecentReauthentication(BasePermission):
    """Every request needs a fresh confirmation."""

    def has_permission(self, request, view):
        return require_step_up(request)


class StepUpForWrites(BasePermission):
    """Reading stays free; creating, changing and deleting need a fresh confirmation."""

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or require_step_up(request)


class StepUpForExports(BasePermission):
    """Spreadsheet exports of personal data need a fresh confirmation."""

    def has_permission(self, request, view):
        return getattr(view, "action", None) != "export_excel" or require_step_up(request)
