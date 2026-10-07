"""Field contracts and setup progress, containing no credentials or host values."""

from rest_framework import serializers

from settings_manager.api import serializers as api_serializers
from settings_manager.api.serializers.push_configuration import PushConfigurationSerializer
from settings_manager.api.serializers.security_policy import SecurityPolicySerializer
from settings_manager.models import LDAPConfig, OIDCConfig
from settings_manager.push_configuration import effective_push
from settings_manager.runtime_policy import effective_policy

CATEGORY_LABELS = {
    "general": "Organisation und Erscheinungsbild",
    "member": "Anwesenheitsregeln",
    "service": "Dienstzeiten",
    "training": "Übungsstandards",
    "vocabulary": "Bezeichnungen",
    "order": "Bestellbenachrichtigungen",
    "email": "E-Mail-Versand",
    "ldap": "Verzeichnisanmeldung",
    "oidc": "Single Sign-On",
    "security": "Sitzungsrichtlinien",
    "push": "Push-Benachrichtigungen",
}
FIELD_LABELS = {
    "title": "Anwendungsname",
    "slug": "Organisationsbezeichnung",
    "logo_url": "Öffentliche Logo-Adresse",
    "brand_color": "Grundfarbe",
    "alert_threshold": "Warnung ab so vielen Fehlzeiten",
    "alert_threshold_last_entries": "Betrachtete letzte Dienste",
    "service_start_time": "Standardbeginn",
    "service_end_time": "Standardende",
    "training_start_time": "Standardbeginn neuer Übungen",
    "training_end_time": "Standardende neuer Übungen",
    "default_block_duration_minutes": "Bausteindauer (Minuten)",
    "member_label": "Bezeichnung für Mitglieder",
    "service_label": "Bezeichnung für das Dienstbuch",
    "training_label": "Bezeichnung für die Ausbildungsplanung",
    "equipment_manager_email": "Bestellungen melden an",
    "email_host": "SMTP-Server",
    "email_port": "SMTP-Port",
    "email_use_tls": "STARTTLS verwenden",
    "email_use_ssl": "Direkte TLS-Verbindung verwenden",
    "email_host_user": "SMTP-Benutzername",
    "email_host_password": "SMTP-Passwort",
    "has_email_host_password": "SMTP-Passwort hinterlegt",
    "default_from_email": "Absenderadresse",
    "enabled": "Aktiviert",
    "server_uri": "Verzeichnisserver",
    "start_tls": "STARTTLS verwenden",
    "ca_cert_file": "CA-Zertifikat am Host",
    "ca_cert_content": "CA-Zertifikat (PEM)",
    "disable_cert_validation": "Zertifikatsprüfung ausschalten",
    "bind_dn": "Anmeldekennung",
    "bind_password": "Verzeichnispasswort",
    "has_bind_password": "Passwort hinterlegt",
    "user_search_base_dn": "Suchbereich für Benutzer",
    "user_search_filter": "Suchfilter für Benutzer",
    "group_search_base_dn": "Suchbereich für Gruppen",
    "group_search_filter": "Suchfilter für Gruppen",
    "group_type": "Verzeichnisart",
    "mirror_groups": "Historische Gruppenspiegelung (ohne Rechtewirkung)",
    "require_group": "Erforderliche Verzeichnisgruppe",
    "provider_name": "Name des Anmeldedienstes",
    "issuer_url": "Adresse des Anmeldedienstes",
    "client_id": "Anwendungskennung",
    "client_secret": "Anwendungsgeheimnis",
    "has_client_secret": "Anwendungsgeheimnis hinterlegt",
    "callback_url": "Rücksprungadresse",
    "scope": "Angeforderte Identitätsmerkmale",
    "groups_claim": "Gruppenmerkmal",
    "staff_group": "Historische Staff-Gruppe",
    "admin_group": "Historische Admin-Gruppe",
    "require_group_mapping": "Rollenzuordnung voraussetzen",
    "hide_local_login": "Lokale Anmeldung ausblenden",
    "trust_provider_mfa": "Zwei-Faktor-Nachweis des Anbieters vertrauen",
    "session_idle_timeout_seconds": "Normale Konten: Zeit ohne Aktivität (Sekunden)",
    "session_max_age_seconds": "Normale Konten: maximale Sitzungsdauer (Sekunden)",
    "privileged_session_idle_timeout_seconds": "Verwaltungskonten: Zeit ohne Aktivität (Sekunden)",
    "privileged_session_max_age_seconds": "Verwaltungskonten: maximale Sitzungsdauer (Sekunden)",
    "public_key": "Öffentlicher Geräteschlüssel",
    "private_key": "Privater Versandschlüssel",
    "has_private_key": "Versandschlüssel hinterlegt",
    "subject": "Kontaktadresse (mailto: oder https://)",
}
SERIALIZERS = {
    **{
        name: getattr(api_serializers, cls)
        for name, cls in {
            "general": "GeneralSettingsSerializer",
            "email": "EmailSettingsSerializer",
            "member": "MemberSettingsSerializer",
            "service": "ServiceSettingsSerializer",
            "training": "TrainingSettingsSerializer",
            "vocabulary": "VocabularySettingsSerializer",
            "order": "OrderSettingsSerializer",
            "ldap": "LDAPSettingsSerializer",
            "oidc": "OIDCSettingsSerializer",
        }.items()
    },
    "security": SecurityPolicySerializer,
    "push": PushConfigurationSerializer,
}
HOST_SETTINGS = [
    {
        "label": "Installation, Updates und Notfallzugang",
        "storage": "host",
        "permission": "Hostadministration",
        "effective": "Installations-/Betriebsvorgang",
    },
    {
        "label": "Domain, Ports, Reverse Proxy und TLS",
        "storage": "host",
        "permission": "Hostadministration",
        "effective": "Neustart bzw. Proxy-Neuladung",
    },
    {
        "label": "Datenbank, Redis, Speicherpfade und Hauptschlüssel",
        "storage": "host",
        "permission": "Hostadministration",
        "effective": "Neustart; Schlüssel nur mit Rotation",
    },
    {
        "label": "Backups, Wiederherstellung und Releasewechsel",
        "storage": "host",
        "permission": "Hostadministration",
        "effective": "Betriebsvorgang",
    },
]


def configuration_catalog(view, request, categories):
    from dynamic_preferences.models import GlobalPreferenceModel

    result = {}
    for category in categories:
        permission_category = "general" if category in {"training", "vocabulary"} else category
        if category in {"security", "push"}:
            permission_category = "all"
        runtime = effective_policy() if category == "security" else effective_push() if category == "push" else {}
        mapping = view.CATEGORY_MAPPINGS[category]
        fields = {}
        for name, field in SERIALIZERS[category]().fields.items():
            if name in {"fields"}:
                continue
            source = "database"
            storage = "database"
            if mapping["fields"]:
                storage = "encrypted_preference" if field.write_only else "preference"
                if not GlobalPreferenceModel.objects.filter(section=mapping["prefix"], name=name).exists():
                    source = "default"
            elif category in {"ldap", "oidc"}:
                storage = "encrypted_database" if field.write_only else "database"
            elif field.write_only:
                storage = "encrypted_database"
            effective = "Neue Datensätze" if category in {"service", "training"} else "Nächste Anfrage"
            if category in {"ldap", "oidc"}:
                effective = "Nächste Anmeldung / Synchronisation"
            fields[name] = {
                "label": FIELD_LABELS[name],
                "storage": storage,
                "source": source,
                "locked": field.read_only,
                "secret": field.write_only,
                "effective": effective,
                "type": "boolean"
                if isinstance(field, serializers.BooleanField)
                else "integer"
                if isinstance(field, serializers.IntegerField)
                else "time"
                if isinstance(field, serializers.TimeField)
                else "string",
                "min": getattr(field, "min_value", None),
                "max": getattr(field, "max_value", None),
                "max_length": getattr(field, "max_length", None),
                "allow_blank": getattr(field, "allow_blank", False),
                "choices": list(getattr(field, "choices", {})),
                "validation": str(field.help_text)
                or "Feldformat, Grenzen und Gesamtzustand werden serverseitig geprüft.",
                **runtime.get("fields", {}).get(name, {}),
            }
        result[category] = {
            "label": CATEGORY_LABELS[category],
            "fields": fields,
            "view_permission": f"settings_manager.view_{permission_category}_settings",
            "change_permission": f"settings_manager.change_{permission_category}_settings",
            "can_change": view._check_category_permission(request.user, category, "change"),
        }
    return {"categories": result, "host": HOST_SETTINGS if view._check_category_permission(request.user, "all") else []}


def setup_status(view):
    from departments.models import Department, RoleTemplate
    from departments.role_catalog import ROLE_SPECS

    general = view._get_category_settings("general")
    roles = RoleTemplate.objects.filter(
        key__in=[role.key for role in ROLE_SPECS], group__isnull=False, is_archived=False
    )
    return {
        "organization_configured": bool(general["slug"] or (general["title"] and general["title"] != "JF Manager")),
        "active_departments": Department.objects.filter(is_active=True).count(),
        "standard_roles": roles.count(),
        "expected_standard_roles": len(ROLE_SPECS),
        "administrator_assigned": roles.filter(group__user__is_active=True, key="system_administrator").exists(),
        "email_configured": bool(view._get_category_settings("email")["email_host"]),
        "ldap_enabled": LDAPConfig.objects.filter(enabled=True).exists(),
        "oidc_enabled": OIDCConfig.objects.filter(enabled=True).exists(),
        "push_enabled": effective_push()["enabled"],
    }
