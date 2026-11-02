"""Built-in consent kinds. They seed ``ConsentKind``; admins add further kinds there."""

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

# Offered to parents in the portal from the start; admins can change this per kind.
PORTAL_KINDS = PHOTO_KINDS
# Former yes/no flags: kept for the history, no longer offered.
LEGACY_KINDS = ("dsgvo_internal", "dsgvo_external")
