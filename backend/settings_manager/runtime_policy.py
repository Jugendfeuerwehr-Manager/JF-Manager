"""One effective source for session settings, with explicit environment locks."""

from django.conf import settings
from django.db import connection

from settings_manager.models import SecurityPolicy

POLICY_FIELDS = {
    "session_idle_timeout_seconds": (300, 90 * 86400),
    "session_max_age_seconds": (3600, 365 * 86400),
    "privileged_session_idle_timeout_seconds": (300, 86400),
    "privileged_session_max_age_seconds": (3600, 7 * 86400),
}


def effective_policy():
    installed = SecurityPolicy._meta.db_table in connection.introspection.table_names()
    policy = SecurityPolicy.objects.filter(pk=1).first() if installed else None
    overrides = settings.CONFIGURATION_ENV_OVERRIDES
    result = {}
    fields = {}
    for name, (minimum, maximum) in POLICY_FIELDS.items():
        locked = name.upper() in overrides
        value = getattr(settings, name.upper()) if locked or policy is None else getattr(policy, name)
        result[name] = value
        fields[name] = {
            "source": "environment" if locked else "database" if policy else "default",
            "locked": locked,
            "environment": name.upper(),
            "min": minimum,
            "max": maximum,
            "unit": "seconds",
            "effective": "next_session_check",
        }
    return {**result, "fields": fields}
