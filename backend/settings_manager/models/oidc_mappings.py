from django.db import models


class OIDCGroupMapping(models.Model):
    """
    Maps an OIDC group claim value to a department role assignment.

    When a user logs in via OIDC and the groups_claim contains this group value,
    a UserDepartmentRole for the configured department is automatically
    created/updated and the specified Django auth groups are assigned.

    This enables automatic permission provisioning based on OIDC group membership.

    Example:
        OIDC group "jf-admins"
        → Department "Hauptwache" + auth.Group "Jugendwart-Verwalter"

    Mirrors the pattern of LDAPDepartmentRoleMapping.
    """

    oidc_config = models.ForeignKey(
        "settings_manager.OIDCConfig",
        on_delete=models.CASCADE,
        related_name="group_mappings",
        verbose_name="OIDC Konfiguration",
    )
    group_claim_value = models.CharField(
        max_length=500,
        verbose_name="Gruppen-Claim Wert",
        help_text=(
            "Der Wert im Gruppen-Claim des OIDC-Tokens, z.B. 'jf-admins' oder 'Jugendwart'. "
            "Nutzer mit diesem Gruppen-Wert erhalten automatisch die konfigurierte Abteilungs-Rolle."
        ),
    )
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.CASCADE,
        related_name="oidc_group_mappings",
        verbose_name="Abteilung",
        null=True,
        blank=True,
    )
    auth_groups = models.ManyToManyField(
        "auth.Group",
        blank=True,
        related_name="oidc_group_mappings",
        verbose_name="Berechtigungsgruppen",
        help_text=(
            "Django-Gruppen, die dem Nutzer in dieser Abteilung zugewiesen werden. "
            "Diese Gruppen steuern, welche Aktionen der Nutzer in der Abteilung ausführen darf."
        ),
    )
    revoke_on_mismatch = models.BooleanField(
        default=False,
        verbose_name="Rolle entfernen wenn nicht (mehr) in OIDC-Gruppe",
        help_text=(
            "Falls aktiviert, wird die Abteilungs-Rolle beim nächsten Login automatisch entfernt, "
            "wenn der Nutzer nicht (mehr) in der OIDC-Gruppe ist. "
            "Standardmäßig deaktiviert: einmal zugewiesene Rollen bleiben erhalten."
        ),
    )

    class Meta:
        verbose_name = "OIDC Gruppen-Mapping"
        verbose_name_plural = "OIDC Gruppen-Mappings"
        unique_together = [["oidc_config", "group_claim_value", "department"]]
        ordering = ["department__name", "group_claim_value"]

    def __str__(self):
        return f"{self.group_claim_value} → {self.department}"
