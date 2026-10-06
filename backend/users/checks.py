"""Deployment checks for state that must be shared between server processes."""

from django.conf import settings
from django.core.checks import Error, Tags, register

PROCESS_LOCAL_CACHES = {
    "django.core.cache.backends.locmem.LocMemCache",
    "django.core.cache.backends.dummy.DummyCache",
}


@register(Tags.security, deploy=True)
def shared_cache_check(app_configs, **kwargs):
    """Login/MFA rate limits and OIDC one-time state live in the default cache.

    A per-process cache multiplies every limit by the number of workers and lets
    an OIDC state be redeemed once per process.
    """
    backend = settings.CACHES.get("default", {}).get("BACKEND", "")
    if backend in PROCESS_LOCAL_CACHES:
        return [
            Error(
                "Der Standard-Cache ist prozesslokal; Anmeldelimits und OIDC-Einmalmarken wären nicht wirksam.",
                hint="REDIS_URL auf einen gemeinsamen Redis setzen (siehe docs/operations/production-security.md).",
                id="users.E001",
            )
        ]
    return []
