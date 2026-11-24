from rest_framework.throttling import AnonRateThrottle


class AdmissionCodeThrottle(AnonRateThrottle):
    """Public voucher endpoints: limits guessing codes per IP address."""

    scope = "admission_code"
    rate = "10/min"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}
