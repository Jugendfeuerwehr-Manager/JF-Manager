# Verschlüsselung und Rotation

## Neuinstallation

`FIELD_ENCRYPTION_KEY` ist für jeden Start verpflichtend, auch lokal. Einen neuen Fernet-Schlüssel einmalig mit `python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'` erzeugen und im geschützten Secret Store beziehungsweise einer nur für den Dienst lesbaren Umgebungsdatei hinterlegen. `jfctl install` erzeugt ihn bei Neuinstallation selbst und übernimmt ihn bei Wiederherstellung und Migration aus der Sicherung. Schlüssel nicht committen, protokollieren oder zusammen mit frei zugänglichen Datenbankbackups ablegen. Alle Web-/Worker-Prozesse benötigen denselben Schlüsselring.

## Update bestehender Installationen

1. Web-/Worker-Schreibzugriffe und Sync-Jobs anhalten. Datenbank und Schlüssel separat sichern; Rückkehr erfordert dieses Backup. Die Sync-Vorwärtsmigration ist absichtlich nicht rückwärts entschlüsselnd.
2. Den bisher tatsächlich verwendeten Schlüssel sichern. Falls kein individueller Schlüssel konfiguriert war, wurde der konstante Ersatzschlüssel der alten Version verwendet. Diesen ausdrücklich aus der bisherigen Installation übernehmen; die neue Version kennt keinen automatischen Ersatz.
3. Neuen individuellen Primärschlüssel als `FIELD_ENCRYPTION_KEY` setzen. Den bisherigen Schlüssel vorübergehend als `FIELD_ENCRYPTION_PREVIOUS_KEYS` setzen (mehrere ältere Schlüssel kommasepariert). Niemals den bekannten alten Ersatz als neuen Primärschlüssel weiterbetreiben.
4. `python manage.py migrate` verschlüsselt bestehende Sync-JSON-Zugangsdaten atomar mit dem neuen Primärschlüssel. LDAP/OIDC bleiben mit dem expliziten alten Schlüssel lesbar. Bei falschem Schlüssel oder beschädigter Chiffre bricht der Zugriff ab.
5. `python manage.py rotate_field_encryption` prüft alle Sync-/LDAP-/OIDC- und MFA-Geheimnisfelder ohne Schreibzugriff. Danach `python manage.py rotate_field_encryption --apply` ausführen. Der Schreibvorgang ist atomar, sperrt betroffene Datensätze und meldet nur die Anzahl. Ein Fehler rollt alle Änderungen zurück.
6. `FIELD_ENCRYPTION_PREVIOUS_KEYS` entfernen, alle Prozesse neu starten und den Prüfbefehl nochmals ausschließlich mit dem neuen Schlüssel ausführen. Erst dann den Betrieb freigeben. Alte Schlüssel nur so lange geschützt aufbewahren, wie verschlüsselte Backups sie benötigen.
7. **Anschließend Zugangsdaten beim jeweiligen Anbieter rotieren:** Spond-/Hi-Org-Kennwörter beziehungsweise Tokens, LDAP-Bindpasswort und OIDC-Clientsecret neu ausstellen und im Manager aktualisieren. Reine Umverschlüsselung widerruft die alten Zugangsdaten nicht. Bereits vorhandene Datenbankkopien enthielten Sync-Geheimnisse im Klartext beziehungsweise mit bekanntem Ersatzschlüssel; deren Zugriff begrenzen und Aufbewahrung prüfen.

Für reguläre spätere Schlüsselrotationen Schritte 1, 3, 5 und 6 wiederholen. Datenbank und Schlüsselring müssen im Restore zusammenpassen. Produktive Schlüssel oder Zugangsdaten werden durch Repository-Änderungen nicht automatisch rotiert.
