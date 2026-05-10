import django.db.models.deletion
import encrypted_model_fields.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("settings_manager", "0003_ldapdepartmentrolemapping"),
        ("departments", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="OIDCConfig",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("enabled", models.BooleanField(default=False, verbose_name="OIDC aktiviert")),
                (
                    "provider_name",
                    models.CharField(
                        default="SSO",
                        help_text="Wird auf dem Login-Button angezeigt, z.B. 'Nextcloud', 'Keycloak' oder 'SSO'.",
                        max_length=100,
                        verbose_name="Anzeigename des Providers",
                    ),
                ),
                (
                    "issuer_url",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Die Basis-URL des OIDC Providers.",
                        max_length=500,
                        verbose_name="Issuer URL",
                    ),
                ),
                (
                    "client_id",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Die Client-ID aus der OIDC-Provider-Konfiguration.",
                        max_length=255,
                        verbose_name="Client ID",
                    ),
                ),
                (
                    "client_secret",
                    encrypted_model_fields.fields.EncryptedCharField(
                        blank=True,
                        default="",
                        help_text="Das Client-Secret. Wird verschlüsselt gespeichert.",
                        max_length=1000,
                        verbose_name="Client Secret",
                    ),
                ),
                (
                    "scope",
                    models.CharField(
                        default="openid email profile",
                        help_text="Leerzeichen-getrennte OIDC-Scopes.",
                        max_length=255,
                        verbose_name="Scopes",
                    ),
                ),
                (
                    "groups_claim",
                    models.CharField(
                        default="groups",
                        help_text="Name des JWT-Claims für Gruppen.",
                        max_length=100,
                        verbose_name="Gruppen-Claim",
                    ),
                ),
                (
                    "staff_group",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Nutzer in dieser Gruppe erhalten is_staff=True.",
                        max_length=255,
                        verbose_name="Staff-Gruppe",
                    ),
                ),
                (
                    "admin_group",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Nutzer in dieser Gruppe erhalten is_superuser=True.",
                        max_length=255,
                        verbose_name="Admin-Gruppe",
                    ),
                ),
                (
                    "require_group_mapping",
                    models.BooleanField(
                        default=False,
                        help_text="Login blockieren wenn kein Gruppen-Mapping passt.",
                        verbose_name="Login nur bei Gruppen-Mapping erlauben",
                    ),
                ),
                (
                    "hide_local_login",
                    models.BooleanField(
                        default=False,
                        help_text="Lokales Passwort-Formular auf Login-Seite ausblenden.",
                        verbose_name="Lokalen Login ausblenden",
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "OIDC Konfiguration",
                "verbose_name_plural": "OIDC Konfiguration",
            },
        ),
        migrations.CreateModel(
            name="OIDCGroupMapping",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "oidc_config",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="group_mappings",
                        to="settings_manager.oidcconfig",
                        verbose_name="OIDC Konfiguration",
                    ),
                ),
                (
                    "group_claim_value",
                    models.CharField(
                        help_text="Der Gruppen-Wert im OIDC-Token.",
                        max_length=500,
                        verbose_name="Gruppen-Claim Wert",
                    ),
                ),
                (
                    "department",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="oidc_group_mappings",
                        to="departments.department",
                        verbose_name="Abteilung",
                    ),
                ),
                (
                    "auth_groups",
                    models.ManyToManyField(
                        blank=True,
                        related_name="oidc_group_mappings",
                        to="auth.group",
                        verbose_name="Berechtigungsgruppen",
                    ),
                ),
                (
                    "revoke_on_mismatch",
                    models.BooleanField(
                        default=False,
                        help_text="Rolle entfernen wenn nicht mehr in OIDC-Gruppe.",
                        verbose_name="Rolle entfernen wenn nicht (mehr) in OIDC-Gruppe",
                    ),
                ),
            ],
            options={
                "verbose_name": "OIDC Gruppen-Mapping",
                "verbose_name_plural": "OIDC Gruppen-Mappings",
                "ordering": ["department__name", "group_claim_value"],
                "unique_together": {("oidc_config", "group_claim_value", "department")},
            },
        ),
        migrations.AlterModelOptions(
            name="settingscategory",
            options={
                "permissions": [
                    ("view_general_settings", "Kann allgemeine Einstellungen einsehen"),
                    ("change_general_settings", "Kann allgemeine Einstellungen \u00e4ndern"),
                    ("view_email_settings", "Kann E-Mail Einstellungen einsehen"),
                    ("change_email_settings", "Kann E-Mail Einstellungen \u00e4ndern"),
                    ("view_member_settings", "Kann Mitglieder Einstellungen einsehen"),
                    ("change_member_settings", "Kann Mitglieder Einstellungen \u00e4ndern"),
                    ("view_service_settings", "Kann Dienst Einstellungen einsehen"),
                    ("change_service_settings", "Kann Dienst Einstellungen \u00e4ndern"),
                    ("view_order_settings", "Kann Bestell Einstellungen einsehen"),
                    ("change_order_settings", "Kann Bestell Einstellungen \u00e4ndern"),
                    ("view_ldap_settings", "Kann LDAP Einstellungen einsehen"),
                    ("change_ldap_settings", "Kann LDAP Einstellungen \u00e4ndern"),
                    ("view_oidc_settings", "Kann OIDC Einstellungen einsehen"),
                    ("change_oidc_settings", "Kann OIDC Einstellungen \u00e4ndern"),
                    ("view_all_settings", "Kann alle Einstellungen einsehen"),
                    ("change_all_settings", "Kann alle Einstellungen \u00e4ndern"),
                ],
                "verbose_name": "Einstellungskategorie",
                "verbose_name_plural": "Einstellungskategorien",
            },
        ),
    ]
