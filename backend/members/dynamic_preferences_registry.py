from django import forms
from dynamic_preferences.preferences import Section
from dynamic_preferences.registries import global_preferences_registry
from dynamic_preferences.types import BooleanPreference, IntegerPreference, StringPreference

general = Section("general")
members = Section("members")
service = Section("service")
email = Section("email")  # New section for email settings
training = Section("training")
orders = Section("orders")  # New section for order settings


@global_preferences_registry.register
class SiteTitle(StringPreference):
    section = general
    name = "title"
    verbose_name = "Seitetitel"
    default = "JF Manager"
    required = False


@global_preferences_registry.register
class SiteSlug(StringPreference):
    section = general
    name = "slug"
    verbose_name = "Organisations-Kürzel"
    help_text = "Kurzbezeichnung der Organisation (z.B. 'JF Berlin'). Wird auf der Loginseite angezeigt."
    default = ""
    required = False


@global_preferences_registry.register
class SiteLogoUrl(StringPreference):
    section = general
    name = "logo_url"
    verbose_name = "Logo URL"
    help_text = "Öffentlich erreichbare URL zum Logo der Organisation. Wird auf der Loginseite angezeigt."
    default = ""
    required = False


@global_preferences_registry.register
class SiteBrandColor(StringPreference):
    section = general
    name = "brand_color"
    verbose_name = "Farbschema"
    help_text = "Grundfarbe der Oberfläche als Hex-Wert (#rrggbb). Kontraststarke Abstufungen werden daraus abgeleitet."
    default = "#b91c1c"
    required = False


@global_preferences_registry.register
class MemberAlertThreshold(IntegerPreference):
    section = members
    name = "alert_threshold"
    verbose_name = "Alarm: Schwellenwert nicht Anwesend"
    help_text = (
        "Definiert den Schwellenwert wann ein Ausrufezeichen angezeigt wird. Berechnet wird hier z.B. 3 von <Intervalgröße>."
        "Daher: Wenn das Mitglied 3 von X nicht da war, wird das Flag angezeigt."
    )
    default = 3
    required = False


@global_preferences_registry.register
class MemberAlertThresholdLastEntries(IntegerPreference):
    section = members
    verbose_name = "Alarm: Intervallgröße"
    help_text = "Definiert die Anzahl an Diensten die Rückwertig betrachtet werden."
    name = "alert_threshold_last_entries"
    default = 10
    required = False


@global_preferences_registry.register
class ServiceStartTime(StringPreference):
    section = service
    name = "service_start_time"
    verbose_name = "Standard Start Zeit"
    default = "18:00"
    required = False


@global_preferences_registry.register
class ServiceEndTime(StringPreference):
    section = service
    name = "service_end_time"
    verbose_name = "Standard Ende Zeit"
    default = "19:30"
    required = False


# Email settings
@global_preferences_registry.register
class EmailHost(StringPreference):
    section = email
    name = "email_host"
    verbose_name = "SMTP Server"
    help_text = "Hostname oder IP-Adresse des SMTP-Servers (z.B. smtp.gmail.com)"
    default = ""
    required = False


@global_preferences_registry.register
class EmailPort(IntegerPreference):
    section = email
    name = "email_port"
    verbose_name = "SMTP Port"
    help_text = "Port des SMTP-Servers (z.B. 587 für TLS, 465 für SSL)"
    default = 587
    required = False


@global_preferences_registry.register
class EmailUseTLS(BooleanPreference):
    section = email
    name = "email_use_tls"
    verbose_name = "TLS verwenden"
    help_text = "TLS-Verschlüsselung für die E-Mail-Verbindung verwenden"
    default = True
    required = False


@global_preferences_registry.register
class EmailUseSSL(BooleanPreference):
    section = email
    name = "email_use_ssl"
    verbose_name = "SSL verwenden"
    help_text = "SSL-Verschlüsselung für die E-Mail-Verbindung verwenden (nicht zusammen mit TLS)"
    default = False
    required = False


@global_preferences_registry.register
class EmailHostUser(StringPreference):
    section = email
    name = "email_host_user"
    verbose_name = "SMTP Benutzername"
    help_text = "Benutzername für die Authentifizierung beim SMTP-Server"
    default = ""
    required = False


@global_preferences_registry.register
class EmailHostPassword(StringPreference):
    from settings_manager.secret_preferences import EncryptedPreferenceSerializer

    serializer = EncryptedPreferenceSerializer
    section = email
    name = "email_host_password"
    verbose_name = "SMTP Passwort"
    help_text = "Passwort für die Authentifizierung beim SMTP-Server"
    default = ""
    required = False
    field_kwargs = {
        "widget": forms.PasswordInput(render_value=False),
    }


@global_preferences_registry.register
class DefaultFromEmail(StringPreference):
    section = email
    name = "default_from_email"
    verbose_name = "Absender E-Mail"
    help_text = "E-Mail-Adresse, die als Absender verwendet wird"
    default = "webmaster@localhost"
    required = False


# Order settings
@global_preferences_registry.register
class EquipmentManagerEmail(StringPreference):
    section = orders
    name = "equipment_manager_email"
    verbose_name = "Gerätewart E-Mail"
    help_text = "E-Mail-Adresse des Gerätewarts für Bestellübersichten"
    default = ""
    required = False


# Defaults apply only when creating new records; existing plans remain unchanged.
for preference_name, preference_default, preference_label in [
    ("training_start_time", "18:00", "Standardbeginn neuer Übungen"),
    ("training_end_time", "20:00", "Standardende neuer Übungen"),
]:
    global_preferences_registry.register(
        type(
            preference_name,
            (StringPreference,),
            {
                "section": training,
                "name": preference_name,
                "default": preference_default,
                "verbose_name": preference_label,
                "required": False,
            },
        )
    )


@global_preferences_registry.register
class TrainingBlockDuration(IntegerPreference):
    section = training
    name = "default_block_duration_minutes"
    default = 15
    verbose_name = "Standarddauer neuer Bausteine (Minuten)"
    required = False


for preference_name, preference_default in [
    ("member_label", "Mitglieder"),
    ("service_label", "Dienstbuch"),
    ("training_label", "Ausbildung"),
]:
    global_preferences_registry.register(
        type(
            preference_name,
            (StringPreference,),
            {
                "section": general,
                "name": preference_name,
                "default": preference_default,
                "verbose_name": "Modulbezeichnung",
                "required": False,
            },
        )
    )


# Texts of the public login page (CFG-02). Plain text only; the page renders
# them escaped. An empty value hides the text.
LOGIN_PAGE_TEXTS = [
    ("login_eyebrow", "Für eure Jugendfeuerwehr"),
    ("login_headline", "Mehr Zeit für\neuer Team."),
    (
        "login_intro",
        "Mitglieder, Dienste und Ausbildung. Alles an einem Ort, damit ihr euch auf das Wesentliche konzentrieren könnt.",
    ),
    ("login_footer", "Gemeinsam organisiert. Gemeinsam stark."),
    ("login_help", "Noch keinen Zugang? Wende dich an die Administration deiner Jugendfeuerwehr."),
]

for preference_name, preference_default in LOGIN_PAGE_TEXTS:
    global_preferences_registry.register(
        type(
            preference_name,
            (StringPreference,),
            {
                "section": general,
                "name": preference_name,
                "default": preference_default,
                "verbose_name": "Text der Anmeldeseite",
                "required": False,
            },
        )
    )
