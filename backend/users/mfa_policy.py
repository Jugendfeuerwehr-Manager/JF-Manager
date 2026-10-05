"""Who must use MFA, and enforcement for every session-based request.

MFA is mandatory for superusers, staff (Django admin), accounts with
administrative rights and delegating leadership roles. Everyone else may opt in.
"""

import time

from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.models import Permission
from django.http import HttpResponseRedirect, JsonResponse

from users.mfa import MFA_VERIFIED_KEY, has_mfa

# Rights that manage accounts, roles, departments or security-relevant settings.
PRIVILEGED_PERMISSIONS = frozenset(
    {
        "users.add_customuser",
        "users.change_customuser",
        "auth.add_group",
        "auth.change_group",
        "departments.add_userdepartmentrole",
        "departments.change_userdepartmentrole",
        "departments.add_roletemplate",
        "departments.change_roletemplate",
        "departments.add_department",
        "departments.change_department",
        "departments.can_manage_all_departments",
        "settings_manager.change_all_settings",
        "settings_manager.change_general_settings",
        "settings_manager.change_email_settings",
        "settings_manager.change_ldap_settings",
        "settings_manager.change_oidc_settings",
    }
)
# Leadership roles that may assign roles to other people (ROLE-02).
DELEGATING_ROLE_KEYS = frozenset({"youth_director", "department_youth_director", "system_administrator"})

POLICY_KEY = "_mfa_policy"
POLICY_RECHECK_SECONDS = 60
# Reachable without MFA so a privileged account can enrol and sign out.
ENROLMENT_PATHS = frozenset(
    {
        "/api/v1/auth/session/",
        "/api/v1/auth/session/logout/",
        "/api/v1/auth/reauthenticate/",
        "/api/v1/auth/mfa/",
        "/api/v1/auth/mfa/setup/",
        "/api/v1/auth/mfa/confirm/",
        "/api/v1/users/me/",
    }
)


def _role_groups(user):
    from django.contrib.auth.models import Group

    return Group.objects.filter(department_assignments__user=user)


def mfa_required(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    if PRIVILEGED_PERMISSIONS & user.get_all_permissions():
        return True
    role_groups = _role_groups(user)
    scoped = Permission.objects.filter(group__in=role_groups).values_list("content_type__app_label", "codename")
    if PRIVILEGED_PERMISSIONS & {f"{app}.{codename}" for app, codename in scoped}:
        return True
    keys = set(user.groups.filter(role_template__isnull=False).values_list("role_template__key", flat=True))
    keys |= set(role_groups.filter(role_template__isnull=False).values_list("role_template__key", flat=True))
    return bool(DELEGATING_ROLE_KEYS & keys)


def mfa_state(user):
    """'verify' if the user owns an authenticator, 'enrol' if one is mandatory, else None."""
    if has_mfa(user):
        return "verify"
    if mfa_required(user):
        return "enrol"
    return None


def is_mfa_verified(session):
    return session.get(MFA_VERIFIED_KEY) is not None


class MFAPolicyMiddleware:
    """Block privileged sessions that lack a verified second factor."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.enforce(request)
        return response if response is not None else self.get_response(request)

    def enforce(self, request):
        session = getattr(request, "session", None)
        user = getattr(request, "user", None)
        if session is None or user is None or not user.is_authenticated or is_mfa_verified(session):
            return None
        now = int(time.time())
        cached = session.get(POLICY_KEY)
        if cached and now - cached["checked_at"] < POLICY_RECHECK_SECONDS:
            state = cached["state"]
        else:
            state = mfa_state(user)
            session[POLICY_KEY] = {"state": state, "checked_at": now}
        if state is None:
            return None
        if state == "verify":
            # A login that skipped the second factor (old session, admin form).
            logout(request)
            return None
        if request.path in ENROLMENT_PATHS:
            return None
        if request.path.startswith("/api/"):
            return JsonResponse(
                {"detail": "Für dieses Konto muss zuerst MFA eingerichtet werden.", "code": "mfa_setup_required"},
                status=403,
            )
        return HttpResponseRedirect(f"{settings.FRONTEND_URL.rstrip('/')}/profile?mfa=setup")
