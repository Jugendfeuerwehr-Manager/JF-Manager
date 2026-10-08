# Störungen und Notfallzugang

## Oberfläche nicht erreichbar

1. `sudo jfctl status` und `sudo jfctl doctor` ausführen; Rückgabecodes und genaue Fehler notieren.
2. DNS, HTTPS/Reverse Proxy, freien Speicher und die gemeldeten Dienste prüfen.
3. `sudo jfctl logs jfctl` sowie Protokolle des betroffenen Dienstes lesen.
4. Bei einer fehlgeschlagenen Änderung den ausgewiesenen Zustand klären, bevor ein weiterer Update-/Restore-Vorgang gestartet wird. Code 6 bezeichnet eine fehlgeschlagene Prüfung nach Änderung, Code 7 einen wiederhergestellten vorherigen Zustand.

## Administrationszugang verloren

Zuerst Identität und Berechtigung der Person prüfen. Mit autorisiertem Hostzugang:

```sh
sudo jfctl admin reset-mfa --user NAME
# Nur wenn zusätzlich das Passwort zurückgesetzt werden muss:
sudo jfctl admin recover --user NAME --reset-mfa
```

`NAME` durch das betroffene Konto ersetzen. Der Reset entfernt Authenticator-App, Passkeys und Wiederherstellungscodes und beendet Sitzungen. Pflichtkonten richten bei der nächsten Anmeldung einen neuen Faktor ein. Für privilegierte Konten ist dieser Hostweg vorgeschrieben. Das neue Passwort wird nicht als Kommandoargument übergeben.

## Schlüssel oder Server verloren

Datenbank und verschlüsselte Zugangsdaten benötigen den passenden alten Schlüsselring. Ein neu erzeugter Schlüssel kann alte Geheimnisse nicht wiederherstellen. Benötigt werden lesbare vollständige Sicherung, Backup-Passwort und passende Version. Ein neuer Host wird mit `jfctl install`, Aktion `restore`, eingerichtet. Danach Hostadresse/HTTPS, Passkeys und angehaltene Worker prüfen.

Bei beschädigten oder nicht entschlüsselbaren Geheimnissen keine neuen Schlüssel über den Bestand schreiben. [Schlüsselrotation](../../operations/encryption-rotation.md) beschreibt die kontrollierte Gesamtprüfung.

## Verdächtiger Zugriff

Berechtigungen und Herkunft prüfen, betroffene Konten/Sitzungen sperren und Protokolle sichern. Versand und Synchronisation bei Bedarf mit `sudo jfctl workers hold` anhalten. Eine Wiederherstellung kann Daten ersetzen; Ziel und Sicherungsstand zuerst mit den Verantwortlichen abstimmen. Nach Behebung Konten, Anmeldefaktoren, Schlüssel und Warteschlangen prüfen, bevor Worker wieder freigegeben werden.
