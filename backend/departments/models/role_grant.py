from django.conf import settings
from django.db import models


class RoleGrant(models.Model):
    """Assignment provenance only; effective rights remain on Django groups."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="role_grants")
    group = models.ForeignKey("auth.Group", on_delete=models.CASCADE, related_name="role_grants")
    department = models.ForeignKey("departments.Department", null=True, blank=True, on_delete=models.CASCADE)
    source = models.CharField(max_length=10, choices=[("local", "Lokal"), ("ldap", "LDAP"), ("oidc", "OIDC")])
    source_key = models.CharField(max_length=100, default="", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "group", "department", "source", "source_key"],
                condition=models.Q(department__isnull=False),
                name="unique_department_role_grant",
            ),
            models.UniqueConstraint(
                fields=["user", "group", "source", "source_key"],
                condition=models.Q(department__isnull=True),
                name="unique_organization_role_grant",
            ),
            models.CheckConstraint(
                condition=models.Q(source__in=["local", "ldap", "oidc"]), name="valid_role_grant_source"
            ),
        ]
