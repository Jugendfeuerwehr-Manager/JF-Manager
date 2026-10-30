"""Known consent kinds with their labels; services accept further slugs."""

CONSENT_KINDS = {
    "privacy_notice_ack": "Datenschutzhinweise zur Kenntnis genommen",
    "data_processing_guardian": "Einwilligung der Sorgeberechtigten in die Datenverarbeitung",
    "photo_internal": "Fotos intern (App, Aushang, Gruppen)",
    "photo_public": "Fotos öffentlich (Website, Presse, soziale Medien)",
    "confidentiality": "Verpflichtung auf Vertraulichkeit",
    # Carried over from the former yes/no flags on user accounts.
    "dsgvo_internal": "Einwilligung zur internen Datenweitergabe (früheres Kennzeichen)",
    "dsgvo_external": "Einwilligung zur externen Datenweitergabe (früheres Kennzeichen)",
}

PHOTO_KINDS = ("photo_internal", "photo_public")
