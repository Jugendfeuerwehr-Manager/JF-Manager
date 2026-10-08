# E-Mail, externe Anmeldung und Synchronisation

## SMTP und Vorlagen

1. **Einstellungen → E-Mail** öffnen, SMTP-Host, Port, Verschlüsselung und Absender passend zum Anbieter eintragen.
2. Zugangsdaten speichern. Ein leeres unverändertes Passwortfeld ersetzt kein vorhandenes Passwort.
3. **Verbindung testen** prüft die Verbindung ohne Nachricht.
4. **Test-E-Mail senden** mit einer eigenen freigegebenen Empfängeradresse und ausdrücklicher Bestätigung verwenden.
5. Vorlagen und Layouts unter **E-Mail-Vorlagen** prüfen. Die angebotenen Platzhalter verwenden und Vorschau kontrollieren.
6. Mit einer berechtigten Fachperson einen gezielten Versand durchführen und den E-Mail-Verlauf prüfen.

Bei Verbindungsfehlern Host, Port, TLS und Zugangsdaten mit dem Anbieter abgleichen. Bei einem Fehler zum Verschlüsselungsschlüssel das Serverteam einbeziehen; ein neuer Hauptschlüssel allein entschlüsselt keine alten Zugangsdaten.

## LDAP

Unter **Einstellungen → LDAP** Verbindung, Suchbasis und Bind-/Suchparameter für euer Verzeichnis pflegen. Vor Aktivierung Verbindung testen. Gruppenmappings beziehen sich auf freigegebene Rollenvorlagen und deren erlaubten Bereich. Bei jeder Zuordnung externe Gruppe, Rolle, Abteilung und Entzugsregel prüfen.

Eine lokal zusätzlich zugewiesene Rolle bleibt unabhängig vom Verzeichnis bestehen. Teste Anmeldung, Gruppenzugehörigkeit und späteren Entzug mit einem nicht privilegierten Testkonto. Lade keine unkontrollierte Sammlung von Verzeichnisgruppen als lokale Rechte.

## Single Sign-On über OIDC

1. Beim Anbieter einen passenden Client für die öffentliche Adresse anlegen. Die Callback-Adresse ist `https://EURE-DOMAIN/api/v1/auth/oidc/callback/`.
2. Unter **Einstellungen → OIDC / SSO** Issuer, Clientangaben und Anzeigenamen eintragen; Discovery testen.
3. Der Anbieter muss PKCE mit S256 unterstützen. Authorization- und Token-Endpunkt liegen über HTTPS auf dem Host der Issuer-URL.
4. Gruppen-Claim und Rollenmapping gezielt konfigurieren. Die tatsächliche Herkunft später auf der Rollenseite prüfen.
5. Anmeldung und Entzug mit einem Testkonto prüfen, bevor ihr die bisherige Anmeldung einschränkt.
6. **MFA des Providers anerkennen** nur verwenden, wenn der Anbieter MFA erzwingt und diese per `amr` meldet. Andernfalls benötigen Pflichtkonten einen eigenen zweiten Faktor.

Die Weboberfläche verwendet auch bei SSO Cookie-Sitzungen. Sie speichert kein JWT für spätere API-Anfragen. [Sitzungen, MFA und Passkeys](../../operations/session-auth.md) enthält die technischen Grenzen. Ein lokales Administrationskonto und der Hostzugang bleiben für Störungen nötig.

## Mitgliedersynchronisation

Unter **Einstellungen → Mitglieder → Mitglieder Synchronisation** verwaltest du Aufträge. Spond ist implementiert; HiOrg ist ein Platzhalter.

1. Anbieter, Bereich (Organisation oder Abteilung) und Betriebsmodus wählen. Zugangsdaten geschützt hinterlegen.
2. Bei Spond prüfen, ob Gruppen zu Mitgliedergruppen oder Abteilungen werden beziehungsweise nur Mitglieder übernommen werden sollen.
3. Verbindung testen. Anfangs manuell ausführen und Löschungen im Prüfmodus behandeln.
4. Ergebnis und Laufhistorie prüfen; erst danach Intervallbetrieb freigeben.
5. Vor einer Bereinigung die Löschvorschau kontrollieren. Automatisches Löschen nur nach fachlicher Prüfung des Verfahrens aktivieren.

Zeitplanung und Ausführung benötigen Wartung und Hintergrundworker. Bleibt ein Auftrag liegen, Betriebsstatus prüfen und das Serverteam einbeziehen. Nach Restore sind Worker absichtlich angehalten, bis Versand und Synchronisation geprüft wurden.

Details zu Aufträgen und Anbietererweiterungen: [Externe Synchronisation](../../domains/external-sync-spond.md).
