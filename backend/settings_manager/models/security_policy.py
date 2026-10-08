from django.db import models


class SecurityPolicy(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    session_idle_timeout_seconds = models.PositiveIntegerField(default=30 * 86400)
    session_max_age_seconds = models.PositiveIntegerField(default=90 * 86400)
    privileged_session_idle_timeout_seconds = models.PositiveIntegerField(default=8 * 3600)
    privileged_session_max_age_seconds = models.PositiveIntegerField(default=8 * 3600)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(id=1), name="security_policy_singleton")]
