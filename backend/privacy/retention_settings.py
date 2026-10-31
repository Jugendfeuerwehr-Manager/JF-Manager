"""Retention periods (days) for personal data; edited under Settings > Datenschutz."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Retention:
    name: str
    label: str
    default: int
    minimum: int
    help_text: str


RETENTIONS = (
    Retention(
        "member_anonymize_after_days",
        "Anonymisierung ehemaliger Mitglieder (Tage nach Austritt)",
        365,
        30,
        "Danach bleiben nur Geschlecht, Jahrgang, Ein-/Austritt, Abteilung, Anwesenheit und Qualifikationen. "
        "Die Leitung wird 30 Tage vorher im Eingang informiert.",
    ),
    Retention(
        "portal_account_delete_days",
        "Beendete Portalzugänge löschen (Tage nach letzter Anmeldung)",
        180,
        30,
        "Deaktivierte Eltern- und Mitgliederzugänge ohne verknüpften Datensatz werden gelöscht.",
    ),
    Retention(
        "staff_account_anonymize_days",
        "Deaktivierte Benutzerkonten bereinigen (Tage nach letzter Anmeldung)",
        365,
        90,
        "Adresse, Telefon, E-Mail, Bild und Signatur werden entfernt; der Name bleibt für Verweise erhalten.",
    ),
    Retention(
        "email_history_days",
        "E-Mail-Verlauf (Tage)",
        365,
        30,
        "Versendete E-Mails mit Empfängern, persönlichem Text und Anhängen.",
    ),
    Retention(
        "notification_log_days",
        "Bestell-Benachrichtigungsprotokoll (Tage)",
        180,
        7,
        "Protokoll versendeter Bestellbenachrichtigungen mit Empfängeradresse.",
    ),
    Retention(
        "email_outbox_days",
        "Nicht zustellbare Benachrichtigungs-E-Mails (Tage)",
        90,
        7,
        "Hängende Einträge des E-Mail-Ausgangs mit ihrem Inhalt.",
    ),
    Retention(
        "push_outbox_days",
        "Nicht zustellbare Push-Mitteilungen (Tage)",
        30,
        7,
        "Hängende Einträge des Push-Ausgangs.",
    ),
    Retention(
        "sync_run_days",
        "Synchronisationsläufe (Tage)",
        90,
        7,
        "Protokolle der Abgleiche mit externen Systemen, inklusive Fehlermeldungen.",
    ),
    Retention(
        "portal_changelog_days",
        "Änderungsprotokoll der Stammdaten (Tage)",
        730,
        90,
        "Alte und neue Werte von Änderungen über das Portal und eigene Datensätze.",
    ),
    Retention(
        "absence_illness_days",
        "Abmeldegrund „Krankheit“ (Tage nach dem Dienst)",
        90,
        7,
        "Gesundheitsbezogener Abmeldegrund; danach bleibt nur „abgemeldet“.",
    ),
)

MAXIMUM_DAYS = 3650
FIELDS = tuple(retention.name for retention in RETENTIONS)
