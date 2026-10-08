"""The only API authentication: Django's session cookie with CSRF protection."""

from rest_framework.authentication import SessionAuthentication as DRFSessionAuthentication


class SessionAuthentication(DRFSessionAuthentication):
    """Answer missing or expired sessions with 401 so clients can tell them from 403."""

    def authenticate_header(self, request):
        return 'Session realm="api"'
