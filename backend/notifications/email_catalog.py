"""Catalogue of notification e-mail types (NOTIF-01.3, concept 4.9.3 and appendix A).

Each type has a default template file under ``templates/notifications/emails/``,
a Django subject template, a layout, the variables shown in the template editor
with sample data, and the links a customised template must keep. Contexts are
flat values only (strings, numbers, lists and dicts of those), never model
instances, so templates cannot reach model methods or relations.
"""

COMMON_VARIABLES = [
    {"name": "org", "type": "object", "description": "Organisation", "properties": ["name", "color"]},
    {"name": "recipient", "type": "object", "description": "Empfänger", "properties": ["first_name", "kind"]},
    {
        "name": "links",
        "type": "object",
        "description": "Links (wirken nur nach Anmeldung des adressierten Kontos)",
        "properties": ["open", "preferences", "withdraw", "withdraw_label", "inbox"],
    },
    {"name": "actions", "type": "list", "description": "Schaltflächen: Liste aus label, url, style"},
    {"name": "sent_at", "type": "string", "description": "Versandzeitpunkt"},
]

COMMON_SAMPLE = {
    "org": {"name": "Jugendfeuerwehr Musterstadt", "color": "#B91C1C"},
    "recipient": {"first_name": "Sandra", "kind": "parent"},
    "links": {
        "open": "https://example.invalid/a/BEISPIEL",
        "preferences": "https://example.invalid/portal/profil#mitteilungen",
        "withdraw": "https://example.invalid/a/ABMELDEN",
        "withdraw_label": "Abmelden",
        "inbox": "https://example.invalid/eingang",
    },
    "actions": [
        {"label": "Termin ansehen", "url": "https://example.invalid/a/BEISPIEL", "style": "secondary"},
        {"label": "Abmelden", "url": "https://example.invalid/a/ABMELDEN", "style": "primary"},
    ],
    "sent_at": "08.10.2026, 18:22 Uhr",
}

SESSION_SAMPLE = {
    "title": "Knoten und Stiche",
    "date": "Di 14.10.2026",
    "time": "18:00–20:00 Uhr",
    "place": "Gerätehaus Mitte",
    "public_note": "Wetterfeste Kleidung mitbringen.",
}
SESSION_VARIABLE = {
    "name": "session",
    "type": "object",
    "description": "Dienst",
    "properties": ["title", "date", "time", "place", "public_note"],
}
PERSON_VARIABLE = {"name": "person", "type": "object", "description": "Betroffene Person", "properties": ["first_name"]}

BASE_LINKS = ("links.open", "links.preferences")
PARTICIPATION_LINKS = (*BASE_LINKS, "links.withdraw", "links.withdraw_label")


def _type(label, subject, layout, variables, sample, required=BASE_LINKS):
    return {
        "label": label,
        "subject": subject,
        "layout": layout,
        "variables": [*COMMON_VARIABLES, *variables],
        "sample_data": {**COMMON_SAMPLE, **sample},
        "required_links": required,
    }


CATALOG = {
    "portal_invite": _type(
        "Portal: Einladung",
        "Dein Zugang zu {{ org.name }}",
        "general",
        [
            {
                "name": "invite",
                "type": "object",
                "description": "Einladung",
                "properties": ["expires_at", "children", "kind"],
            }
        ],
        {"invite": {"expires_at": "15.10.2026, 18:00 Uhr", "children": ["Mia", "Jonas"], "kind": "parent"}},
        required=("links.open",),  # invitees have no account yet, so no preferences link
    ),
    "account_link": _type(
        "Konto: Verknüpfung bestätigen",
        "Bitte bestätige die Verknüpfung mit deinem Mitgliedsdatensatz",
        "general",
        [{"name": "link", "type": "object", "description": "Verknüpfung", "properties": ["member_name", "linked_by"]}],
        {"link": {"member_name": "Jana Krüger", "linked_by": "Alex Sommer"}},
    ),
    "cr_submitted": _type(
        "Änderungsantrag gestellt",
        "Änderungsantrag für {{ request.person_name }}",
        "important",
        [
            {
                "name": "request",
                "type": "object",
                "description": "Antrag (nur Kontaktfelder: label, old, new)",
                "properties": ["person_name", "requested_by", "fields", "conflicts"],
            }
        ],
        {
            "request": {
                "person_name": "Mia Becker",
                "requested_by": "Sandra Becker",
                "fields": [{"label": "Mobil", "old": "0151 2345678", "new": "0170 9876543"}],
                "conflicts": 0,
            }
        },
    ),
    "cr_decided": _type(
        "Änderungsantrag entschieden",
        "Dein Änderungsantrag wurde bearbeitet",
        "general",
        [
            {
                "name": "request",
                "type": "object",
                "description": "Ergebnis",
                "properties": ["person_name", "result", "fields", "note"],
            }
        ],
        {
            "request": {
                "person_name": "Mia Becker",
                "result": "übernommen",
                "fields": [{"label": "Mobil", "old": "0151 2345678", "new": "0170 9876543"}],
                "note": "",
            }
        },
    ),
    "reg_cancelled": _type(
        "Kurzfristige Abmeldung",
        "Kurzfristige Abmeldung: {{ session.title }} am {{ session.date }}",
        "important",
        [
            SESSION_VARIABLE,
            {"name": "cancellations", "type": "list", "description": "Abmeldungen: name, reason_category, at"},
            {"name": "counts", "type": "object", "description": "Zähler", "properties": ["expected", "cancelled"]},
            {"name": "staffing", "type": "object", "description": "Besetzung", "properties": ["missing"]},
        ],
        {
            "session": SESSION_SAMPLE,
            "cancellations": [{"name": "Mia Becker", "reason_category": "Krankheit", "at": "heute 16:40"}],
            "counts": {"expected": 11, "cancelled": 3},
            "staffing": {"missing": []},
        },
    ),
    "reg_digest": _type(
        "Meldungen: Tageszusammenfassung",
        "Meldungen von heute ({{ counts.total }})",
        "general",
        [
            {"name": "sessions", "type": "list", "description": "Je Dienst: title, date, counts"},
            {"name": "counts", "type": "object", "description": "Gesamt", "properties": ["total"]},
        ],
        {
            "sessions": [
                {"title": "Knoten und Stiche", "date": "Di 14.10.", "counts": {"registered": 2, "cancelled": 1}}
            ],
            "counts": {"total": 3},
        },
    ),
    "slot_free_manual": _type(
        "Platz frei (Warteliste manuell)",
        "Platz frei: {{ session.title }}",
        "important",
        [
            SESSION_VARIABLE,
            {"name": "slot", "type": "object", "description": "Position", "properties": ["label"]},
            {"name": "waitlist", "type": "number", "description": "Passende Wartende"},
        ],
        {"session": SESSION_SAMPLE, "slot": {"label": "Truppmann/-frau"}, "waitlist": 2},
    ),
    "staffing_at_risk": _type(
        "Mindestbesetzung gefährdet",
        "Mindestbesetzung gefährdet: {{ session.title }}",
        "important",
        [
            SESSION_VARIABLE,
            {"name": "staffing", "type": "object", "description": "Besetzung", "properties": ["missing"]},
        ],
        {"session": SESSION_SAMPLE, "staffing": {"missing": [{"label": "Wachführung", "count": 1}]}},
    ),
    "waitlist_placed": _type(
        "Teilnahme: Warteliste",
        "Warteliste: {{ session.title }}",
        "events",
        [
            PERSON_VARIABLE,
            SESSION_VARIABLE,
            {
                "name": "waitlist",
                "type": "object",
                "description": "Warteliste",
                "properties": ["position", "slot", "auto"],
            },
        ],
        {
            "person": {"first_name": "Mia"},
            "session": SESSION_SAMPLE,
            "waitlist": {"position": 2, "slot": "", "auto": True},
            "links": {**COMMON_SAMPLE["links"], "withdraw_label": "Von der Warteliste abmelden"},
        },
        required=PARTICIPATION_LINKS,
    ),
    "waitlist_promoted": _type(
        "Teilnahme: Nachgerückt",
        "{{ person.first_name }} ist nachgerückt: {{ session.title }}",
        "events",
        [
            PERSON_VARIABLE,
            SESSION_VARIABLE,
            {"name": "deadlines", "type": "object", "description": "Fristen", "properties": ["cancellation"]},
        ],
        {
            "person": {"first_name": "Mia"},
            "session": SESSION_SAMPLE,
            "deadlines": {"cancellation": "Di 14.10., 16:00 Uhr"},
        },
        required=PARTICIPATION_LINKS,
    ),
    "assign_published": _type(
        "Teilnahme: Zuteilung",
        '{% if assignment.result == "assigned" %}Zugeteilt{% else %}Nicht berücksichtigt{% endif %}: {{ session.title }}',
        "events",
        [
            PERSON_VARIABLE,
            SESSION_VARIABLE,
            {
                "name": "assignment",
                "type": "object",
                "description": "Zuteilung",
                "properties": ["result", "slot", "open_for_backfill"],
            },
        ],
        {
            "person": {"first_name": "Mia"},
            "session": SESSION_SAMPLE,
            "assignment": {"result": "assigned", "slot": "Truppmann/-frau", "open_for_backfill": False},
        },
        required=PARTICIPATION_LINKS,
    ),
    "session_changed": _type(
        "Teilnahme: Dienst geändert oder abgesagt",
        '{% if change.kind == "cancelled" %}Abgesagt{% else %}Geändert{% endif %}: {{ session.title }}',
        "important",
        [
            PERSON_VARIABLE,
            SESSION_VARIABLE,
            {"name": "change", "type": "object", "description": "Änderung", "properties": ["kind", "old", "new"]},
        ],
        {
            "person": {"first_name": "Mia"},
            "session": SESSION_SAMPLE,
            "change": {"kind": "moved", "old": "Di 14.10., 18:00 Uhr", "new": "Mi 15.10., 18:00 Uhr"},
        },
        required=PARTICIPATION_LINKS,
    ),
    "session_published": _type(
        "Teilnahme: Neuer Dienst",
        "Neuer Termin: {{ session.title }} am {{ session.date }}",
        "events",
        [
            PERSON_VARIABLE,
            SESSION_VARIABLE,
            {"name": "series", "type": "object", "description": "Serie (optional)", "properties": ["title", "dates"]},
            {
                "name": "deadlines",
                "type": "object",
                "description": "Fristen",
                "properties": ["registration", "cancellation"],
            },
            {"name": "participation", "type": "object", "description": "Teilnahme", "properties": ["mode"]},
        ],
        {
            "person": {"first_name": "Mia"},
            "session": SESSION_SAMPLE,
            "series": {"title": "", "dates": []},
            "deadlines": {"registration": "So 12.10., 18:00 Uhr", "cancellation": "Di 14.10., 16:00 Uhr"},
            "participation": {"mode": "opt_out"},
        },
        required=PARTICIPATION_LINKS,
    ),
    "eligibility_conflict": _type(
        "Voraussetzung nicht mehr erfüllt",
        "Voraussetzung nicht mehr erfüllt: {{ session.title }}",
        "important",
        [SESSION_VARIABLE, {"name": "conflicts", "type": "list", "description": "Konflikte: name, reason"}],
        {
            "session": SESSION_SAMPLE,
            "conflicts": [{"name": "Jonas Becker", "reason": "Qualifikation ‚Truppmann‘ fehlt"}],
        },
    ),
    "parent_access_end": _type(
        "Elternzugriff endet",
        "Elternzugang für {{ person.first_name }} endet am {{ access.ends_at }}",
        "general",
        [PERSON_VARIABLE, {"name": "access", "type": "object", "description": "Zugang", "properties": ["ends_at"]}],
        {"person": {"first_name": "Jonas"}, "access": {"ends_at": "02.11.2026"}},
    ),
}

PARTICIPATION_TYPES = frozenset(k for k, v in CATALOG.items() if "links.withdraw" in v["required_links"])


def template_path(kind):
    return f"notifications/emails/{kind}.html"


def type_choices():
    return [(kind, entry["label"]) for kind, entry in CATALOG.items()]


def variables_catalog():
    return {
        kind: {
            "variables": entry["variables"],
            "sample_data": entry["sample_data"],
            "required_links": list(entry["required_links"]),
        }
        for kind, entry in CATALOG.items()
    }
