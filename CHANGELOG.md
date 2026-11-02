# Änderungsprotokoll

Alle nennenswerten Änderungen je Version. Der Abschnitt einer Version wird beim Release automatisch in die GitHub-Releasebeschreibung übernommen.

## [Unreleased]

## [3.3.1] – 2026-11-02

### Hinweise zum Update

**Vor dem Update bitte lesen.** Ein Update läuft immer mit dem `jfctl` der installierten Version. Bis einschließlich 3.3.0 enthält es den unten beschriebenen Fehler. Ohne diese Schritte kann auch das Update auf 3.3.1 „abgeschlossen“ melden, während die alte Version weiterläuft. Als root:

```bash
# 1. Welche Version läuft wirklich?
readlink /opt/jf-manager/current                      # z. B. releases/3.2.3
grep JF_VERSION /etc/jf-manager/jfctl.conf

# 2. Nur wenn beide Versionen abweichen: eingetragene Version auf die laufende setzen
sed -i 's/^JF_VERSION=.*/JF_VERSION=3.2.3/' /etc/jf-manager/jfctl.conf

# 3. Fehlenden Schlüssel eintragen (bisheriges Verhalten, bleibt stehen)
grep -q '^CSP_REPORT_ONLY=' /etc/jf-manager/app.env || echo 'CSP_REPORT_ONLY=false' >> /etc/jf-manager/app.env

# 4. Backup prüfen, aktualisieren, kontrollieren
jfctl backup list
jfctl update --version 3.3.1
readlink /opt/jf-manager/current                      # releases/3.3.1
jfctl doctor
```

- Die Reihenfolge einhalten und für diese Schritte nicht `jfctl config set` verwenden. `config set` schreibt die Version aus `jfctl.conf` in die Compose-Konfiguration; ein Neustart würde dann neue Images ohne Migration starten.
- Meldet `jfctl backup list` ein fehlendes Repository und gab es noch nie eine Sicherung, das Repository vorab von Hand anlegen. Der alte `jfctl` kann das noch nicht: `RESTIC_PASSWORD_FILE=/etc/jf-manager/backup.pass restic -r <JF_BACKUP_REPO aus jfctl.conf> init`.
- Ab 3.3.1 erkennt `jfctl` beide Probleme selbst. Spätere Updates brauchen diese Schritte nicht mehr.
- Keine Datenbankmigrationen.

### Behoben

- **`jfctl update` wechselt wieder wirklich auf die neue Version.** Seit 3.1.0 brach ein Update in Stufe 4 mit „unerwarteter Abbruch“ ab, wenn in `/etc/jf-manager/app.env` kein `CSP_REPORT_ONLY` stand. Das ist der Normalfall. Der Rückfall auf die alte Version lief dann nur in einem Teilprozess, und das Update machte danach weiter. Am Ende meldete jfctl „Update abgeschlossen“ und trug die neue Version ein, gestartet blieb aber die alte (#25). Ein fehlender Schlüssel gilt jetzt als „CSP durchsetzen“. Ein Rückfall läuft nur noch im eigentlichen Update-Prozess. Weicht die eingetragene Version von der laufenden ab, meldet `jfctl doctor` das, und `jfctl update` geht von der tatsächlich laufenden Version aus.
- **Fehlendes Backup-Repository blockiert Sicherung und Update nicht mehr.** `jfctl backup create` und `jfctl update` meldeten bei einem fehlenden Repository nur „nicht erreichbar oder Passwort falsch“ und legten es nie an. Jetzt unterscheiden sie: Repository fehlt, Passwort falsch, Ziel nicht erreichbar. Die Prüfung läuft vor dem Wartungsfenster. Hat die Installation noch nie eine Sicherung abgeschlossen, legt jfctl das Repository selbst an. Fehlt es nach erfolgreichen Sicherungen, bricht jfctl ab, statt still ein leeres Repository anzulegen. Neu: `jfctl backup init`. `jfctl doctor` prüft das Repository mit (#25).

## [3.3.0] – 2026-11-02

### Neu

- **Gemeinsame Dienste für alle Abteilungen.** Für Termine der ganzen Organisation, etwa eine Vollversammlung, gibt es beim Anlegen die Abteilung „Alle Abteilungen (gemeinsamer Dienst)“. Das können nur Konten mit organisationsweitem Zugriff wählen. Solche Dienste erscheinen in jeder Abteilung, gekennzeichnet mit „Alle Abteilungen“. Jede Abteilungsleitung erfasst dort die Anwesenheit ihrer eigenen Mitglieder. Bearbeiten und Löschen bleiben organisationsweiten Konten vorbehalten.
- **Abteilung in der Dienstliste.** In der Ansicht „Alle Abteilungen“ steht bei jedem Dienst, zu welcher Abteilung er gehört (am Desktop und mobil).

### Geändert

- **Kommende Dienste in der richtigen Reihenfolge.** Unter „Kommend“ steht der nächste Dienst immer oben, vergangene Dienste tauchen dort nicht mehr auf. Vorher konnte ein Ladevorgang im Hintergrund nach dem Anmelden oder beim Wechsel der Abteilung die Liste mit allen Diensten in absteigender Reihenfolge überschreiben.
- **„Anwesenheit offen“ als eigener Bereich.** Vergangene Dienste, bei denen noch Anwesenheiten fehlen, stehen am Desktop über den kommenden Diensten in einem eigenen Bereich (wie bisher schon in der mobilen Ansicht).
- **Neues Übungs-Handout zum Arbeiten während der Ausbildung.** PDF und Druckansicht zeigen auf der ersten Seite den Ablaufplan maßstäblich: Die Höhe eines Blocks entspricht seiner Dauer, Blöcke für mehrere oder alle Gruppen sind ein durchgehender Kasten, mit Ort und Ausbildern. Danach folgen „Wer ist wo?“ mit allen Einsätzen je Ausbilder und unbesetzten Stationen, Laufzettel je Gruppe und ein eigenes Blatt je Station zum Austeilen (Durchgänge zum Abhaken, Lernziel, Sicherheit, Material-Checkliste, Ablauf, Notizlinien). Zum Schluss kommen eine Packliste zum Abhaken und die Anmerkungen.
- **Handout im Branding der Organisation.** Das Handout übernimmt das gewählte Farbschema und das Logo der Organisation (ohne eigenes Logo das JF-Manager-Zeichen). Block-Inhalte behalten Überschriften, Listen und Hervorhebungen; Bilder werden auch als WebP oder SVG eingebettet. Am Bildschirm erscheint das Handout als weißes Blatt auf dem Seitenhintergrund.

### Behoben

- **Neue Dienste landen auch bei Admin-Konten in der richtigen Abteilung.** Ist oben eine Abteilung gewählt, wird der Dienst genau dort angelegt. Fehlt die Abteilung, etwa weil im Browser nach dem Update noch die alte Oberfläche lief, speichert das System bei organisationsweiten Konten keinen Dienst ohne Abteilung mehr. Stattdessen bittet es um die Auswahl, außer es gibt nur eine Abteilung. In der Ansicht „Alle Abteilungen“ fragt das Formular nach der Abteilung. Dienste, die durch den Fehler ohne Abteilung gespeichert wurden, erscheinen jetzt als gemeinsame Dienste und lassen sich im Formular einer Abteilung zuordnen (#25).

### Sicherheit

- `pyasn1` (indirekte Abhängigkeit, ASN.1-Verarbeitung) auf 0.6.5 aktualisiert, um vier bekannte Sicherheitslücken zu schließen.
- `follow-redirects` (indirekte Abhängigkeit der Oberfläche über axios) auf 1.16.2 aktualisiert: Bei Weiterleitungen konnten Zugangsdaten an ein anderes Ziel gelangen.

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
