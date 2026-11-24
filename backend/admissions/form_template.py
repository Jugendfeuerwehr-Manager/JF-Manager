"""Sample application form of a youth fire brigade, modelled on a typical paper application."""

GUARDIAN_FIELDS = [
    {"target": "guardian.name", "required": True},
    {"target": "guardian.lastname", "required": True},
    {"target": "guardian.street", "required": False},
    {"target": "guardian.zip_code", "required": False},
    {"target": "guardian.city", "required": False},
    {"target": "guardian.phone", "required": False},
    {"target": "guardian.mobile", "required": True},
    {"target": "guardian.email", "required": True},
]

UNDER_18 = {"age_below": 18}

COMMITMENT_HTML = (
    "<p>Ich verpflichte mich,</p><ol>"
    "<li>an den Veranstaltungen der Jugendfeuerwehr regelmäßig, pünktlich und in vollständiger Dienstkleidung "
    "teilzunehmen. Ausnahmen sind Urlaub, Krankheit, Schule, berufliche Verpflichtungen oder dringende persönliche "
    "Angelegenheiten; die Jugendfeuerwehr ist dann zu informieren.</li>"
    "<li>Dienstkleidung, Geräte und Fahrzeuge pfleglich zu behandeln und nur dienstlich zu nutzen.</li>"
    "<li>durch kameradschaftliches Verhalten zu einem guten Zusammenhalt beizutragen.</li>"
    "<li>den kürzesten Weg zwischen Wohnung und Feuerwehrhaus zu nehmen, da sonst kein Versicherungsschutz besteht.</li>"
    "<li>Hin- und Heimweg in Absprache mit den Erziehungsberechtigten selbst zu organisieren.</li>"
    "<li>bei allen Veranstaltungen die Regelungen des Jugendschutzgesetzes einzuhalten.</li>"
    "</ol><p>Bei Missachtung kann ein Ausschluss aus der Jugendfeuerwehr erfolgen.</p>"
)


def _section(section_id, title, elements):
    return {"id": section_id, "title": title, "elements": elements}


def jf_template():
    return {
        "pages": [
            {
                "id": "p_person",
                "title": "Personalien",
                "sections": [
                    _section(
                        "s_person",
                        "Angaben zur Person",
                        [
                            {
                                "id": "e_name",
                                "type": "text",
                                "key": "vorname",
                                "label": "Vorname",
                                "target": "member.name",
                                "required": True,
                            },
                            {
                                "id": "e_lastname",
                                "type": "text",
                                "key": "nachname",
                                "label": "Nachname",
                                "target": "member.lastname",
                                "required": True,
                            },
                            {
                                "id": "e_birthday",
                                "type": "date",
                                "key": "geburtsdatum",
                                "label": "Geburtsdatum",
                                "target": "member.birthday",
                                "required": True,
                            },
                            {
                                "id": "e_gender",
                                "type": "select",
                                "key": "geschlecht",
                                "label": "Geschlecht",
                                "target": "member.gender",
                                "required": True,
                                "help": "Wird für die Jahresstatistik der Jugendfeuerwehr benötigt.",
                            },
                            {
                                "id": "e_pronouns",
                                "type": "text",
                                "key": "pronomen",
                                "label": "Pronomen",
                                "required": False,
                            },
                            {
                                "id": "e_street",
                                "type": "text",
                                "key": "strasse",
                                "label": "Straße, Hausnr.",
                                "target": "member.street",
                                "required": True,
                            },
                            {
                                "id": "e_zip",
                                "type": "text",
                                "key": "plz",
                                "label": "PLZ",
                                "target": "member.zip_code",
                                "required": True,
                            },
                            {
                                "id": "e_city",
                                "type": "text",
                                "key": "ort",
                                "label": "Ort",
                                "target": "member.city",
                                "required": True,
                            },
                            {
                                "id": "e_phone",
                                "type": "phone",
                                "key": "telefon",
                                "label": "Telefon",
                                "target": "member.phone",
                            },
                            {
                                "id": "e_mobile",
                                "type": "phone",
                                "key": "mobil",
                                "label": "Mobil",
                                "target": "member.mobile",
                            },
                            {
                                "id": "e_email",
                                "type": "email",
                                "key": "email",
                                "label": "E-Mail-Adresse",
                                "target": "member.email",
                            },
                        ],
                    ),
                    _section(
                        "s_guardians",
                        "Erziehungsberechtigte",
                        [
                            {
                                "id": "e_guardians",
                                "type": "guardians",
                                "key": "sorgeberechtigte",
                                "label": "Erziehungsberechtigte",
                                "min": 1,
                                "max": 2,
                                "fields": GUARDIAN_FIELDS,
                                "visible_if": UNDER_18,
                            },
                        ],
                    ),
                ],
            },
            {
                "id": "p_more",
                "title": "Weitere Angaben",
                "sections": [
                    _section(
                        "s_school",
                        "Schul- oder Berufsverhältnis (freiwillig)",
                        [
                            {
                                "id": "e_school",
                                "type": "text",
                                "key": "schule_arbeitgeber",
                                "label": "Name der Schule / des Arbeitgebers",
                            },
                            {
                                "id": "e_career",
                                "type": "text",
                                "key": "berufsziel",
                                "label": "Berufsausbildung / voraussichtliches Berufsziel",
                            },
                        ],
                    ),
                    _section(
                        "s_clubs",
                        "Vereine und Organisationen (freiwillig)",
                        [
                            {
                                "id": "e_clubs",
                                "type": "textarea",
                                "key": "vereine",
                                "label": "Ich bin aktives Mitglied in folgenden Vereinen/Organisationen",
                            },
                        ],
                    ),
                    _section(
                        "s_health",
                        "Gesundheit",
                        [
                            {
                                "id": "e_swim",
                                "type": "checkbox",
                                "key": "schwimmer",
                                "label": "Ich kann schwimmen",
                                "target": "member.canSwimm",
                            },
                            {
                                "id": "e_insurance",
                                "type": "text",
                                "key": "krankenversicherung",
                                "label": "Krankenversicherung (freiwillig)",
                            },
                            {
                                "id": "e_health",
                                "type": "textarea",
                                "key": "gesundheit",
                                "label": "Bekannte Krankheiten, Behinderungen, Beschwerden und Allergien (auch Arzneimittelunverträglichkeiten), freiwillig",
                                "target": "member.health_notes",
                            },
                        ],
                    ),
                    _section(
                        "s_photo",
                        "Passbild",
                        [
                            {
                                "id": "e_photo_hint",
                                "type": "richtext",
                                "html": "<p>Das Passbild wird für den Ausweis der Deutschen Jugendfeuerwehr verwendet.</p>",
                            },
                            {
                                "id": "e_photo",
                                "type": "photo",
                                "key": "passbild",
                                "label": "Passbild",
                                "target": "member.avatar",
                            },
                        ],
                    ),
                ],
            },
            {
                "id": "p_consent",
                "title": "Datenschutz und Einwilligungen",
                "sections": [
                    _section(
                        "s_privacy",
                        "Datenschutz",
                        [
                            {
                                "id": "e_privacy",
                                "type": "legal_ack",
                                "key": "datenschutz",
                                "label": "Ich habe die Datenschutzhinweise gelesen.",
                                "legal_kind": "privacy",
                                "required": True,
                            },
                            {
                                "id": "e_data_applicant",
                                "type": "consent",
                                "key": "einwilligung_daten",
                                "label": "Datenspeicherung zu Verwaltungszwecken",
                                "consent_kind": "data_processing_applicant",
                                "person": "applicant",
                                "required": True,
                            },
                            {
                                "id": "e_data_guardian",
                                "type": "consent",
                                "key": "einwilligung_daten_eltern",
                                "label": "Einwilligung der gesetzlichen Vertreter",
                                "consent_kind": "data_processing_guardian",
                                "person": "guardians",
                                "required": True,
                                "visible_if": UNDER_18,
                            },
                            {
                                "id": "e_photo_internal",
                                "type": "consent",
                                "key": "fotos_intern",
                                "label": "Fotos intern",
                                "consent_kind": "photo_internal",
                                "person": "applicant",
                            },
                            {
                                "id": "e_photo_public",
                                "type": "consent",
                                "key": "fotos_oeffentlich",
                                "label": "Fotos öffentlich",
                                "consent_kind": "photo_public",
                                "person": "applicant",
                            },
                            {
                                "id": "e_continue_ea",
                                "type": "consent",
                                "key": "fortgeltung_ea",
                                "label": "Fortgeltung bei Übertritt in die Einsatzabteilung",
                                "consent_kind": "consent_continues_ea",
                                "person": "applicant",
                            },
                        ],
                    ),
                ],
            },
            {
                "id": "p_sign",
                "title": "Verpflichtung und Unterschrift",
                "sections": [
                    _section(
                        "s_commitment",
                        "Erklärung und Verpflichtung",
                        [
                            {"id": "e_commitment", "type": "richtext", "html": COMMITMENT_HTML},
                            {
                                "id": "e_commitment_ack",
                                "type": "checkbox",
                                "key": "verpflichtung",
                                "label": "Ich habe die Erklärung zur Kenntnis genommen.",
                                "required": True,
                            },
                            {
                                "id": "e_sign_applicant",
                                "type": "signature",
                                "key": "unterschrift_antragsteller",
                                "label": "Unterschrift Antragsteller*in",
                                "role": "applicant",
                                "required": True,
                            },
                            {
                                "id": "e_sign_guardian_1",
                                "type": "signature",
                                "key": "unterschrift_sorgeberechtigte_1",
                                "label": "Unterschrift 1. Erziehungsberechtigte*r",
                                "role": "guardian_1",
                                "required": True,
                                "visible_if": UNDER_18,
                            },
                            {
                                "id": "e_sign_guardian_2",
                                "type": "signature",
                                "key": "unterschrift_sorgeberechtigte_2",
                                "label": "Unterschrift 2. Erziehungsberechtigte*r",
                                "role": "guardian_2",
                                "visible_if": UNDER_18,
                            },
                        ],
                    ),
                ],
            },
        ]
    }
