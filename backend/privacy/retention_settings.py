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
