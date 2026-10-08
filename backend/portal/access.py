"""Which routes a portal account (parent, member) may reach at all.

Deny by default: a portal account reaches only the routes named here or views
that declare ``portal_access = True`` and check their own object binding. Every
other route, including new ones, answers 403 before the view runs.
"""

# Own sign-in, second factor, devices, own account profile and password,
# plus anonymous login-page data. Push stays closed until the portal category
# exists (NOTIF-01.5): the current categories carry staff notifications.
PORTAL_ALLOWED_VIEW_NAMES = frozenset(
    {
        "session-status",
        "session-login",
        "session-logout",
        "session-mfa",
        "session-passkey",
        "session-passkey-options",
        "session-mfa-passkey-options",
        "reauthenticate",
        "reauth-passkey-options",
        "devices",
        "devices-revoke-others",
        "device-revoke",
        "mfa-status",
        "mfa-setup",
        "mfa-confirm",
        "mfa-recovery-codes",
        "mfa-disable",
        "mfa-totp-remove",
        "passkey-register-begin",
        "passkey-register-finish",
        "passkey-remove",
        "customuser-me",
        "customuser-change-password",
        "customuser-request-password-reset",
        "customuser-reset-password",
        "public-branding",
        "oidc-public-config",
        "csp-report",
        "health_check",
    }
)

FORBIDDEN_DETAIL = "Mit einem Portalzugang ist diese Funktion nicht verfügbar."
FORBIDDEN_CODE = "portal_account_forbidden"


def is_portal_account(user):
    return bool(user and user.is_authenticated and getattr(user, "account_kind", None) == "portal")


def _view_class(func):
    return getattr(func, "cls", None) or getattr(func, "view_class", None)


def portal_route_allowed(match):
    """``match`` is a ResolverMatch; None (unknown route) is never allowed."""
    if match is None:
        return False
    if match.view_name in PORTAL_ALLOWED_VIEW_NAMES:
        return True
    view = _view_class(match.func) or match.func
    return getattr(view, "portal_access", False) is True
