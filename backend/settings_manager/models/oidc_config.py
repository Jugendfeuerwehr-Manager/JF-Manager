from django.core.exceptions import ValidationError
from django.db import models
from encrypted_model_fields.fields import EncryptedCharField


class OIDCConfig(models.Model):
    """
    Singleton-style DB model for OpenID Connect (OIDC/OAuth2) configuration.

    Supports any standard OIDC provider (Nextcloud, Keycloak, etc.).
    One record is always used; retrieved via get_or_create_default().
    """

    enabled = models.BooleanField(default=False, verbose_name="OIDC aktiviert")

    provider_name = models.CharField(
        max_length=100,
        default="SSO",
        verbose_name="Anzeigename des Providers",
        help_text="Wird auf dem Login-Button angezeigt, z.B. 'Nextcloud', 'Keycloak' oder 'SSO'.",
    )

    issuer_url = models.CharField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="Issuer URL",
        help_text=(
            "Die Basis-URL des OIDC Providers. Das Discovery-Dokument wird unter "
            "{issuer_url}/.well-known/openid-configuration gesucht. "
            "Für Nextcloud z.B. https://nextcloud.example.org."
        ),
    )

    client_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Client ID",
        help_text="Die Client-ID aus der OIDC-Provider-Konfiguration.",
    )

    client_secret = EncryptedCharField(
        max_length=1000,
        blank=True,
        default="",
        verbose_name="Client Secret",
        help_text="Das Client-Secret aus der OIDC-Provider-Konfiguration. Wird verschlüsselt gespeichert.",
    )

    scope = models.CharField(
        max_length=255,
        default="openid email profile",
        verbose_name="Scopes",
        help_text="Leerzeichen-getrennte OIDC-Scopes. Standard: 'openid email profile'. "
        "Für Nextcloud-Gruppen-Claim zusätzlich 'groups' hinzufügen.",
    )

    groups_claim = models.CharField(
        max_length=100,
        default="groups",
        verbose_name="Gruppen-Claim",
        help_text=(
            "Name des JWT-Claims, der die Gruppen-Zugehörigkeiten des Nutzers enthält. "
            "Standard bei Nextcloud OIDC: 'groups'."
        ),
    )

    staff_group = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Staff-Gruppe",
        help_text=(
            "Nutzer in dieser Gruppe erhalten automatisch is_staff=True (Zugang zum Admin-Bereich). "
            "Leer lassen, um kein automatisches Staff-Mapping vorzunehmen."
        ),
    )

    admin_group = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Admin-Gruppe",
        help_text=(
            "Nutzer in dieser Gruppe erhalten automatisch is_superuser=True. "
            "Leer lassen, um kein automatisches Superuser-Mapping vorzunehmen."
        ),
    )

    require_group_mapping = models.BooleanField(
        default=False,
        verbose_name="Login nur bei Gruppen-Mapping erlauben",
        help_text=(
            "Falls aktiviert, wird der Login blockiert, wenn der Nutzer in keiner konfigurierten "
            "Gruppen-Zuordnung (OIDC-Gruppen-Mapping) enthalten ist. "
            "Standardmäßig deaktiviert: Nutzer erhalten Zugang, auch ohne Abteilungszuweisung."
        ),
    )

    hide_local_login = models.BooleanField(
        default=False,
        verbose_name="Lokalen Login ausblenden",
        help_text=(
            "Falls aktiviert, wird das lokale Benutzername/Passwort-Formular auf der Login-Seite "
            "standardmäßig ausgeblendet. Ein kleiner Link ermöglicht es Administratoren, "
            "sich trotzdem mit lokalem Account anzumelden."
        ),
    )

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "OIDC Konfiguration"
        verbose_name_plural = "OIDC Konfiguration"

    def __str__(self):
        return f"OIDC Config ({self.provider_name})"

    def clean(self):
        if not self.enabled:
            return

        required_when_enabled = {
            "issuer_url": self.issuer_url,
            "client_id": self.client_id,
        }
        missing = [field for field, value in required_when_enabled.items() if not value]
        if missing:
            raise ValidationError({field: "Dieses Feld ist erforderlich wenn OIDC aktiviert ist." for field in missing})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @classmethod
    def get_or_create_default(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
