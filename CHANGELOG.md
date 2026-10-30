# Änderungsprotokoll

Alle nennenswerten Änderungen je Version. Der Abschnitt einer Version wird beim Release automatisch in die GitHub-Releasebeschreibung übernommen.

## [3.2.3] – 2026-10-30

### Behoben

- **Neue Dienste landen in der richtigen Abteilung.** Neu angelegte Dienste werden in der aktiven Abteilung gespeichert (vorher ohne Abteilung, dadurch 404 beim Öffnen). Das Anlegen ohne Abteilung wird für Nutzer mit mehreren Abteilungen abgelehnt, und die Zielabteilung beim Anlegen und Verschieben wird abteilungsgenau geprüft (#25).
- **Datumsfelder behalten den gewählten Tag.** Beim Speichern eines Datumsfelds (etwa Geburtstag, Qualifikation oder Dienst) wurde in Zeitzonen östlich von UTC, also auch in Deutschland, der Vortag gespeichert (aus 01.05. wurde 30.04.). Der ausgewählte Tag bleibt jetzt erhalten, und auch der Ablauf von Qualifikationen wird mit dem richtigen Kalendertag berechnet.

### Sicherheit

- Abhängigkeiten mit bekannten Sicherheitslücken aktualisiert: Pillow (Bildverarbeitung), Django REST Framework, certifi und DOMPurify. Dabei wurde die Fehlerauswertung der Slot-Konfiguration an die neue Fehlerform des Frameworks angepasst.
- Das Backend-Image enthält die aktuelle `tzdata` (Debian-Sicherheitsupdate DLA-4854-1).
- Die Pipeline-Workflows erhalten nur noch Lesezugriff auf das Repository, und die Weiterleitung per `hardNavigate` folgt ausschließlich Pfaden der eigenen Anwendung.

## [3.2.1] – 2026-10-12

### Geändert

- **Eine Dienstseite für alle Wege.** Ein Dienst öffnet sich jetzt immer gleich, egal ob aus dem Dienstbuch, aus der Ausbildungsplanung, aus der Handy-Ansicht oder vom Dashboard. Erster Reiter ist „Dienstdaten“ mit Termin, Ort, Leitung, Beschreibung und Nachbereitung; danach folgen Meldungen, Anwesenheit und Betreuende. Wer den Dienst nicht bearbeiten darf, sieht die Dienstdaten zum Lesen und zusätzlich den Reiter „Vorkommnisse“. Der Anwesenheits-Link in der Dienstliste öffnet weiterhin direkt „Anwesenheit“.
- **Übungen sichtbar löschen.** Abgesagte Übungen zeigen im Planer oben den Hinweis „Diese Übung ist abgesagt“ mit dem Knopf „Übung löschen“. Die Handy-Ansicht einer Übung hat jetzt ebenfalls „Löschen“. Im Planer-Menü „Weitere Aktionen“ steht „Löschen“ wie bisher.
- Der Link vom Planer zum Dienstbuch heißt jetzt „Dienst im Dienstbuch“.

## [3.2.0] – 2026-10-11

### Neu

- **Meldungen an Verwaltende.** Meldet sich jemand an, bewirbt sich (auch auf eine Position) oder meldet sich ab, erhalten alle Verwaltenden der Abteilung einschließlich Administration einen Eintrag im Eingang, eine E-Mail und eine Push-Mitteilung. Mehrere Meldungen zu einem Dienst werden in einer E-Mail zusammengefasst; wer die Meldung selbst erfasst hat, bekommt keine Mail.
- **Bewerbungen zuteilen.** Bewerbungen erzeugen im Eingang je Dienst eine Aufgabe „Bewerbungen zuteilen“. Sie wird automatisch erledigt, sobald die Zuteilung veröffentlicht ist oder keine Bewerbung mehr offen ist. Zugeteilte Personen werden wie bisher benachrichtigt.
- **Schnellerfassung.** In „Meldungen“ stehen alle Personen ohne Rückmeldung alphabetisch als Namensflächen. Ein Tipp erfasst die Anmeldung bzw. Bewerbung, zum Beispiel vom Papierzettel; optional mit Wunschposition. Von Betreuenden erfasste Meldungen sind gekennzeichnet.
- **Um Rückmeldung bitten.** Ein Knopf in „Meldungen“ fragt alle Personen ohne Rückmeldung per Portal, E-Mail und Push (höchstens einmal pro Stunde je Dienst). Personen ohne Portalkonto werden gezählt, damit sie persönlich gefragt werden können.
- **Neue Rückmeldungen auf einen Blick.** Kalender, Planer und Handy-Ansicht zeigen, wie viele neue Rückmeldungen seit dem letzten Öffnen der Meldungen eingegangen sind.
- **Übung löschen im Planer** über das Menü „Weitere Aktionen“, mit Hinweis, dass Teilnehmende dabei nicht benachrichtigt werden.

### Geändert

- Abmeldungen werden Verwaltenden jetzt immer per E-Mail und Push gemeldet, nicht nur kurz vor dem Dienst.
- Zum Löschen einer Übung genügt jetzt das Planungsrecht der Abteilung. Bisher fehlte den Planungsrollen das Löschrecht, sodass nur „Absagen“ möglich war.
- Neue Mitteilungsarten „Neue Anmeldungen und Bewerbungen“ und „Bitten um Rückmeldung“; alle Arten sind unter „Profil → Mitteilungen“ einzeln abschaltbar.

### Entfernt

- Veraltete OpenAPI-Datei `backend/schema.yml` aus dem Repository (die Anwendung liefert ihre Schnittstellenbeschreibung weiterhin selbst aus).

### Hinweise zum Update

- Enthält Datenbankmigrationen (`orders.0018`, `participation.0005`); sie laufen beim Update mit `jfctl` automatisch.
