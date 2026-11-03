# Überblick und Rollen

## Verantwortlicher und Auftragsverarbeiter

- **Verantwortlich** (Art. 4 Nr. 7 DSGVO) ist der Träger der Jugendfeuerwehr bzw. des Vereins, in der Regel die Gemeinde/Stadt oder der Feuerwehrverein. Teilen sich mehrere Abteilungen eine Installation, bleibt der Träger verantwortlich; die Abteilungstrennung der Anwendung setzt das „Need-to-know“ zwischen den Abteilungen um.
- **Auftragsverarbeiter** (Art. 28) ist, wer die Installation für den Träger betreibt, ohne selbst über Zwecke zu entscheiden: externer Dienstleister, Rechenzentrum, ggf. eine ehrenamtliche Einzelperson mit eigenem Server. Dafür braucht es einen Vertrag ([Vorlage](templates/dpa-outline.md)).
- **Unterauftragsverarbeiter:** Hoster, E-Mail-Versand (SMTP-Anbieter), Speicherort der Sicherungen, ggf. Push-Dienste der Browserhersteller (Inhalte Ende-zu-Ende-verschlüsselt, ohne Namen), Spond/Hi-Org bei aktivierter Synchronisation.

## Betroffene und Daten

| Betroffene | Daten | Besonders schutzwürdig |
| --- | --- | --- |
| Mitglieder (überwiegend minderjährig) | Name, Geburtstag, Geschlecht, Kontakt, Adresse, Gruppe, Status, Ein-/Austritt, Anwesenheit, Teilnahme, Qualifikationen, Ausrüstung, Bestellungen, Bemerkungen, Ausweisbild, Anhänge, Einwilligungen | Gesundheitsangaben (Art. 9), Daten Minderjähriger (Art. 8, ErwGr. 38) |
| Eltern / Sorgeberechtigte | Name, Kontakt, Adresse, Zuordnung zu Kindern, Portalzugang, Einwilligungen | – |
| Betreuende / Leitung | Konto, Rollen, Kontakt, Anwesenheit im Dienst, Qualifikationen, Sitzungen | – |

## Rechtsgrundlagen (Orientierung)

| Verarbeitung | Typische Grundlage |
| --- | --- |
| Mitgliederverwaltung, Dienstbuch, Teilnahme, Qualifikationen | Art. 6 Abs. 1 b (Mitgliedschaft) bzw. e i. V. m. Feuerwehrgesetz/Satzung bei kommunaler Trägerschaft |
| Elternportal, Benachrichtigungen | Art. 6 Abs. 1 b/e; die Kenntnisnahme der Datenschutzhinweise wird mit Version protokolliert, sie ist keine Einwilligung |
| Gesundheitsangaben für Notfälle | Art. 9 Abs. 2 a (ausdrückliche Einwilligung der Sorgeberechtigten) oder c (lebenswichtige Interessen); zweckgebunden |
| Fotos | Art. 6 Abs. 1 a (Einwilligung), getrennt intern/öffentlich, jederzeit widerrufbar |
| Sicherheitsprotokolle, Export-Audit | Art. 6 Abs. 1 c/f i. V. m. Art. 32 |

## Was die Anwendung dazu bereitstellt

- Rechtstexte als versionierte Seiten, öffentlich unter `/impressum` und `/datenschutz`.
- Einwilligungsnachweise je Person mit Version, Herkunft und Widerruf.
- Feldrechte und Abteilungstrennung; Gesundheitsangaben verschlüsselt, nur auf Abruf mit erneuter Bestätigung und protokolliert.
- Löschkonzept mit einstellbaren Fristen, Anonymisierung ehemaliger Mitglieder, Bereinigung beendeter Konten.
- Datenauskunft als ZIP (Art. 15/20).
