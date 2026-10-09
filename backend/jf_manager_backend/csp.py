"""Content-Security-Policy and Permissions-Policy for Django responses (SEC-13).

The policy is enforced by default. ``CSP_REPORT_ONLY=true`` switches to
``Content-Security-Policy-Report-Only`` for troubleshooting; violations go to
``/api/v1/security/csp-report/`` in both modes (see ``csp_report``).

Views with their own, stricter policy (private media: ``sandbox``) keep it.
"""

from django.conf import settings

ENFORCE_HEADER = "Content-Security-Policy"
REPORT_ONLY_HEADER = "Content-Security-Policy-Report-Only"


def build_policy(directives):
    return "; ".join(f"{name} {' '.join(sources)}" for name, sources in directives.items())


def policy_header():
    return REPORT_ONLY_HEADER if settings.CSP_REPORT_ONLY else ENFORCE_HEADER


class ContentSecurityPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if ENFORCE_HEADER not in response and REPORT_ONLY_HEADER not in response:
            response[policy_header()] = build_policy(settings.CSP_DIRECTIVES)
        if "Permissions-Policy" not in response:
            response["Permissions-Policy"] = settings.PERMISSIONS_POLICY
        return response
