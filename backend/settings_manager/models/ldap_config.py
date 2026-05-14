from django.core.exceptions import ValidationError
from django.db import models
from encrypted_model_fields.fields import EncryptedCharField


class LDAPConfig(models.Model):
    class GroupType(models.TextChoices):
        GROUP_OF_NAMES = "group_of_names", "GroupOfNames"
        ACTIVE_DIRECTORY = "active_directory", "ActiveDirectory"

    enabled = models.BooleanField(default=False, verbose_name="LDAP aktiviert")

    server_uri = models.CharField(max_length=255, blank=True, default="", verbose_name="LDAP Server URI")
    start_tls = models.BooleanField(default=False, verbose_name="STARTTLS verwenden")
    ca_cert_file = models.CharField(
        max_length=512,
        blank=True,
        default="",
        verbose_name="CA Zertifikat (Dateipfad)",
        help_text="Optional: Dateipfad zu einer CA-Zertifikatsdatei für LDAP TLS.",
    )
    ca_cert_content = models.TextField(
        blank=True,
        default="",
        verbose_name="CA Zertifikat (Inhalt)",
        help_text="Optional: PEM-Inhalt eines CA-Zertifikats für LDAP TLS.",
    )
    disable_cert_validation = models.BooleanField(
        default=False,
        verbose_name="TLS Zertifikatsprüfung deaktivieren",
        help_text="Nicht empfohlen: Deaktiviert die TLS Zertifikatsprüfung für LDAP Verbindungen.",
    )

    bind_dn = models.CharField(max_length=255, blank=True, default="", verbose_name="Bind DN")
    bind_password = EncryptedCharField(max_length=255, blank=True, default="", verbose_name="Bind Passwort")

    user_search_base_dn = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Benutzer Such-Basis DN",
    )
    user_search_filter = models.CharField(
        max_length=255,
        default="(uid=%(user)s)",
        verbose_name="Benutzer Such-Filter",
        help_text="z.B. (uid=%(user)s) oder (sAMAccountName=%(user)s)",
    )

    group_search_base_dn = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Gruppen OU / Basis DN",
    )
    group_search_filter = models.CharField(
        max_length=255,
        default="(objectClass=groupOfNames)",
        verbose_name="Gruppen Such-Filter",
    )
    group_type = models.CharField(
        max_length=32,
        choices=GroupType.choices,
        default=GroupType.GROUP_OF_NAMES,
        verbose_name="Gruppen Typ",
    )

    mirror_groups = models.BooleanField(
        default=True,
        verbose_name="LDAP Gruppen spiegeln",
        help_text="Spiegelt LDAP Gruppen als Django auth.Group bei Login.",
    )
    require_group = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Require Group DN",
        help_text="Optional: Nur Benutzer dieser LDAP Gruppe dürfen sich anmelden.",
    )

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "LDAP Konfiguration"
        verbose_name_plural = "LDAP Konfiguration"

    def clean(self):
        if not self.enabled:
            return

        required_when_enabled = {
            "server_uri": self.server_uri,
            "user_search_base_dn": self.user_search_base_dn,
            "user_search_filter": self.user_search_filter,
        }

        missing = [field for field, value in required_when_enabled.items() if not value]
        if missing:
            raise ValidationError({field: "Dieses Feld ist erforderlich wenn LDAP aktiviert ist." for field in missing})

        if self.group_search_base_dn and not self.group_search_filter:
            raise ValidationError(
                {"group_search_filter": "Gruppen Such-Filter ist erforderlich wenn Gruppen-Suche gesetzt ist."}
            )

        if self.ca_cert_file and self.ca_cert_content:
            raise ValidationError(
                {
                    "ca_cert_file": "Bitte entweder Dateipfad oder Zertifikatsinhalt verwenden, nicht beides.",
                    "ca_cert_content": "Bitte entweder Dateipfad oder Zertifikatsinhalt verwenden, nicht beides.",
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @classmethod
    def get_or_create_default(cls):
        config = cls.objects.order_by("id").first()
        if config:
            return config
        return cls.objects.create()
