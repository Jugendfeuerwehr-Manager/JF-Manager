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

## Betriebsstatus

Unter **Einstellungen → Betriebsstatus** stehen Version, letzte Sicherung und Hintergrundaufgaben. Bei fehlgeschlagener oder veralteter Sicherung, alten Statusangaben oder angehaltenen Workern das Serverteam informieren. Die Seite ist eine Momentaufnahme der von `jfctl` geschriebenen Datei und bietet keine Hoststeuerung.

Weitere Feldregeln und Beispiele: [Einrichtung und Konfiguration](../../domains/configuration.md).
