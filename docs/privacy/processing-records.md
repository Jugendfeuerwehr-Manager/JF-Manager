# Verzeichnis von Verarbeitungstätigkeiten (Vorlage, Art. 30)

Je Tätigkeit ausfüllen und um Träger, Kontakt der oder des Datenschutzbeauftragten und Empfänger ergänzen. Die Spalte „Löschung“ verweist auf die Fristen in der Anwendung ([data-retention.md](../operations/data-retention.md)).

| Tätigkeit | Zweck | Betroffene / Daten | Empfänger | Löschung |
| --- | --- | --- | --- | --- |
| Mitgliederverwaltung | Organisation der Jugendgruppe | Mitglieder: Stamm-, Kontakt-, Gruppendaten, Bemerkungen, Bild, Anhänge | Leitung der Abteilung nach Rolle | Anonymisierung nach Austritt (Standard 365 Tage) |
| Gesundheitsangaben | Hilfe im Notfall bei Übungen und Fahrten | Mitglieder: Allergien, Medikamente, Notfallhinweise | Nur Rollen mit Gesundheitsrecht, jeder Abruf protokolliert | Mit Anonymisierung/Löschung des Mitglieds |
| Eltern und Portal | Kontakt, Abmeldungen, Datenänderungen durch Eltern | Eltern: Stamm- und Kontaktdaten, Portalkonto | Leitung; anderer Elternteil nur mit Freigabe | Portalzugang endet automatisch; Konto 180 Tage danach gelöscht |
| Dienstbuch und Anwesenheit | Nachweis der Dienste, Jahresstatistik | Mitglieder, Betreuende: Anwesenheit | Leitung, Dienstverantwortliche | Bleibt am anonymisierten Datensatz |
| Teilnahme und Abmeldungen | Planung von Übungen | Mitglieder: Meldestatus, Abmeldegrund | Dienstverantwortliche | Kurztext 90 Tage, Grund „Krankheit“ 90 Tage nach dem Dienst |
| Qualifikationen und Sonderaufgaben | Ausbildungsnachweis | Mitglieder, Betreuende | Leitung, Qualifikationsverwaltung | Bleiben am anonymisierten Datensatz, Notizen werden geleert |
| Inventar und Bestellungen | Ausgabe von Ausrüstung | Mitglieder: Name, Größen, Buchungen | Inventar-/Bestellverwaltung | Name in Buchungen wird bei Anonymisierung entfernt |
| E-Mail-Versand | Information von Mitgliedern und Eltern | Empfängeradresse, Name, Text, Anhänge | SMTP-Anbieter | 365 Tage |
| Benachrichtigungen (Eingang, Push) | Hinweise an Leitung und Eltern | Konto, Titel | Browser-Push-Dienste (ohne Namen) | 180 Tage bzw. bei Zustellung |
| Konten und Anmeldung | Zugang, Sicherheit | Konto, Rollen, Sitzungen, MFA | – | Deaktivierte Konten nach 365 Tagen bereinigt |
| Synchronisation (optional) | Abgleich mit Spond/Hi-Org | Stamm- und Kontaktdaten | Anbieter der Quelle | Läufe 90 Tage |
| Protokolle | Sicherheit, Nachweis | IP-Adressen (Webserver), Export-Audit | Betreiber | 14 Tage bzw. 180 Tage |
