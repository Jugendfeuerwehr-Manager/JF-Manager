from rest_framework.throttling import SimpleRateThrottle

PORTAL_WRITE_RATE = "30/min"


class PortalWriteThrottle(SimpleRateThrottle):
    """At most 30 writes per minute and account (concept 5.2.6). Reads are not counted."""

    scope = "portal_write"

    def get_rate(self):
        return PORTAL_WRITE_RATE

    def get_cache_key(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS") or not request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}
