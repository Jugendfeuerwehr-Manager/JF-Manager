from django.db import models


class LDAPDepartmentRoleMapping(models.Model):
    """
    Maps an LDAP group DN to a department role assignment.

    When a user who is member of the specified LDAP group logs in, a
    UserDepartmentRole for the configured department will be automatically
    created/updated and the specified Django auth groups will be assigned.

    This enables automatic permission provisioning based on LDAP group membership:

    Example:
        LDAP group "cn=jf-admins,ou=groups,dc=feuerwehr,dc=example,dc=org"
        → Department "Hauptwache" + auth.Group "Jugendwart-Verwalter"

    The user will then be able to access member data for "Hauptwache" according
    to the permissions in "Jugendwart-Verwalter".
    """

    ldap_config = models.ForeignKey(
        "settings_manager.LDAPConfig",
        on_delete=models.CASCADE,
        related_name="department_role_mappings",
        verbose_name="LDAP Konfiguration",
    )
    ldap_group_dn = models.CharField(
        max_length=500,
        verbose_name="LDAP Gruppen-DN",
        help_text=(
            "Vollständiger DN der LDAP-Gruppe, z.B. cn=admins,ou=groups,dc=example,dc=org. "
            "Benutzer in dieser Gruppe erhalten automatisch die konfigurierte Abteilungs-Rolle."
        ),
    )
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.CASCADE,
        related_name="ldap_role_mappings",
        verbose_name="Abteilung",
    )
    auth_groups = models.ManyToManyField(
        "auth.Group",
        blank=True,
        related_name="ldap_role_mappings",
        verbose_name="Berechtigungsgruppen",
        help_text=(
            "Django-Gruppen, die dem Benutzer in dieser Abteilung zugewiesen werden. "
            "Diese Gruppen steuern, welche Aktionen der Benutzer in der Abteilung ausführen darf."
        ),
    )
    revoke_on_mismatch = models.BooleanField(
        default=False,
        verbose_name="Rolle entfernen wenn nicht (mehr) in LDAP-Gruppe",
        help_text=(
            "Falls aktiviert, wird die Abteilungs-Rolle beim nächsten Login automatisch entfernt, "
            "wenn der Benutzer nicht (mehr) Mitglied der LDAP-Gruppe ist. "
            "Standardmäßig deaktiviert: einmal zugewiesene Rollen bleiben erhalten."
        ),
    )

    class Meta:
        verbose_name = "LDAP Abteilungs-Rollen-Mapping"
        verbose_name_plural = "LDAP Abteilungs-Rollen-Mappings"
        unique_together = [["ldap_config", "ldap_group_dn", "department"]]
        ordering = ["department__name", "ldap_group_dn"]

    def __str__(self):
        return f"{self.ldap_group_dn} → {self.department}"
