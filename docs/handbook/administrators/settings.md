# Einstellungen und Stammdaten

Die Einstellungsnavigation zeigt nur Kategorien, für die du Rechte hast. Änderungen bewusst speichern und danach den angezeigten gespeicherten Stand prüfen. Eine geänderte Standardeinstellung bearbeitet normalerweise keine vorhandenen Datensätze rückwirkend.

| Kategorie | Was du dort einrichtest | Wirkung / worauf achten? |
| --- | --- | --- |
| Einrichtung | Geführter Überblick mit Links zu vorhandenen Webverwaltungen | Zeigt den echten Stand; Öffnen verändert nichts |
| Allgemein | Anwendungsname, Organisationsbezeichnung, Logo, Farbe | Logo ist öffentlich; keine privaten Dokumente hochladen |
| Bezeichnungen | Modulnamen für Mitglieder, Dienstbuch und Ausbildungsplanung | Ändert Navigationstexte, keine Daten oder Rechte |
| Anmeldeseite | Überschrift, Einleitung, Kopf-/Fußzeile und Formularhinweis | Öffentlich sichtbarer reiner Text; leere Felder ausblenden |
| Mitglieder | Fachliche Mitgliedereinstellungen | Mit den verantwortlichen Fachpersonen abstimmen |
| Dienste | Standardzeiten und Dienstkonfiguration | Neue Termine prüfen; Beginn muss vor Ende liegen |
| Übungsstandards | Standardbeginn/-ende und Bausteindauer | Gilt für neue Übungen/Bausteine; Dauer 1–480 Minuten |
| Bestellungen | Bestellkonfiguration und Fachverwaltungen | Zulässige Statusübergänge und Benachrichtigungen gemeinsam prüfen |
| E-Mail / E-Mail-Vorlagen | SMTP und Nachrichtenlayouts/-texte | Speichern vor Verbindungstest; Testversand ausdrücklich bestätigen |
| LDAP / OIDC | Verzeichnis, externe Anmeldung und Rollenmapping | Neue Anmeldung mit Testkonto prüfen; lokalen Notfallzugang erhalten |
| Sitzungen | Inaktivität und maximale Dauer, normale/privilegierte Konten | Wirkt bei nächster Sitzungsprüfung; Maximum mindestens Inaktivität |
| Push | Kontaktadresse, Versandschlüssel, Aktivierung | Geräte müssen zusätzlich im eigenen Profil zustimmen |
| Datenschutz | Impressum und Datenschutzerklärung | Veröffentlichte Versionen sind öffentlich und bleiben als Nachweis erhalten |
| Einstellungsübersicht | Speicherung, Herkunft, Regeln und Wirksamkeit | Hostvorgaben sind gesperrt; keine Geheimniswerte angezeigt |
| Betriebsstatus | Version, Sicherung und Workerzustand | Nur lesen; Hoständerungen über `jfctl` |

## Fachstammdaten

Der Einrichtungsassistent verlinkt Gruppen, Anwesenheitsstatus, Ereignisarten, Qualifikations- und Aufgabentypen, Übungsvorlagen, Inventar und Bestellartikel/-abläufe. Diese Bereiche benötigen die jeweilige Fachrolle. Prüfe vor Änderungen, ob vorhandene Daten oder zugewiesene Rollen betroffen sind.

## Herkunft und Geheimnisse

Einstellungen können aus Datenbank oder Hostvorgaben stammen. Prüfe die Einstellungsübersicht, wenn ein Wert gesperrt ist oder eine Änderung keine erwartete Wirkung zeigt. Ein unverändertes leeres Geheimnisfeld erhält den gespeicherten Wert; eine ausdrücklich angebotene Entfernung ist eine andere Aktion. Gespeicherte Geheimnisse werden nicht zurückgegeben.

## Push einrichten

1. Unter **Push** eine gültige Kontaktadresse (`mailto:` oder `https://`) eintragen.
2. **Versandschlüssel sicher erzeugen** wählen, sofern keine vorhanden sind.
3. Push ausdrücklich aktivieren. Im Profil eines Testgeräts Mitteilungen erlauben und Test senden.
4. Zustellung und die Auswahl der Kategorien prüfen.

Schlüsselwechsel schaltet Push aus und erfordert eine erneute Anmeldung aller Geräte. Verändere ein bestehendes Paar nur mit einem abgestimmten Wechselplan. Geplante Teilnahme-Mitteilungen sind noch nicht Teil dieses Handbuchstands.

## Impressum und Datenschutzerklärung

Unter **Datenschutz** pflegst du beide Texte im Editor. **Entwurf speichern** ändert nichts Öffentliches. **Veröffentlichen** friert den Entwurf als neue Version ein. Sie erscheint dann unter `/impressum` bzw. `/datenschutz`, verlinkt auf der Anmeldeseite, im Portal und im Benutzermenü. Ältere Versionen bleiben erhalten und lassen sich nicht ändern.

Nimmt ein Elternteil eine Portal-Einladung an, speichert die Anwendung die Kenntnisnahme mit der dann gültigen Version (z. B. `privacy:v3`). Freiwillige Foto-Einwilligungen aus der Einladung landen beim Kind. Weitere Einwilligungen, etwa nach einem Papierformular, erfasst die Leitung beim Mitglied, beim Elternteil oder am Konto. Ein Widerruf ist ein neuer Eintrag; der Verlauf bleibt vollständig.

Als dritten Text pflegt ihr hier die **Nutzungsregeln Portal** (öffentlich unter `/nutzungsregeln`). Wer bei aktivem Portal die Mitgliedschaft beantragt, bestätigt sie; das wird als Einwilligungsart „Nutzungsregeln des Portals akzeptiert“ mit der gültigen Version gespeichert.

Unter **Einwilligungsarten** legt ihr fest, welche Einwilligungen es gibt, und ergänzt eigene (z. B. „Teilnahme an Ausfahrten“). Für jede Art gibt es einen Wortlaut. Ändert ihr ihn, steigt die Version; bestehende Einwilligungen behalten die Version, für die sie erteilt wurden. Ist **Im Portal anbieten** eingeschaltet, erteilen und widerrufen Eltern die Einwilligung im Portal unter **Einwilligungen** selbst für jedes Kind. Jede Änderung wird mit Datum, Person und Wortlaut protokolliert. Die Jugendwarte der Abteilung des Kindes (Recht „Mitglieder anonymisieren“) bekommen einen Eintrag im Eingang und je nach Einstellung eine E-Mail oder Push-Mitteilung. Mitgelieferte und bereits verwendete Arten lassen sich nicht löschen, nur deaktivieren; ein Widerruf bleibt auch für deaktivierte Arten möglich.

Rechte: `settings_manager.view_privacy_settings` bzw. `change_privacy_settings` (oder die entsprechenden Rechte für alle Einstellungen). Die Texte sind keine Rechtsberatung; lass sie von der oder dem Datenschutzbeauftragten des Trägers prüfen. Vorlagen und Checkliste: [Datenschutz](../../privacy/README.md).

## Betriebsstatus

Unter **Einstellungen → Betriebsstatus** stehen Version, letzte Sicherung und Hintergrundaufgaben. Bei fehlgeschlagener oder veralteter Sicherung, alten Statusangaben oder angehaltenen Workern das Serverteam informieren. Die Seite ist eine Momentaufnahme der von `jfctl` geschriebenen Datei und bietet keine Hoststeuerung.

Weitere Feldregeln und Beispiele: [Einrichtung und Konfiguration](../../domains/configuration.md).
