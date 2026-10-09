# Fehlerhilfe im Alltag

## Wenn etwas fehlt oder nicht klappt

| Situation | Nächster Schritt |
| --- | --- |
| Ein Modul ist nicht sichtbar | Modulsuche verwenden, aktive Abteilung prüfen und benötigte Rechte mit der Administration klären. |
| Ein Jugendlicher fehlt beim Dienst | Mitglieder-Datensatz und Zuordnung zur Abteilung prüfen. |
| Ein Ausbilder fehlt beim Dienst | Aktives Benutzerkonto und Abteilungszuordnung prüfen lassen. |
| Eine Anwesenheitsänderung wurde abgewiesen | Neu geladenen Stand prüfen und bei Bedarf erneut auswählen; möglicherweise wurde dieselbe Person gerade parallel geändert. |
| Der Abgleich ist unterbrochen | Verbindung wiederherstellen und auf die Synchronisationsmeldung achten. Fehlgeschlagene Änderungen erneut prüfen. |
| Eine E-Mail ist fehlgeschlagen | Details im E-Mail-Verlauf öffnen, Adresse korrigieren und gegebenenfalls erneut senden. |
| Push wird nicht angeboten | HTTPS, Browserunterstützung, installierte App auf iOS und Servereinrichtung prüfen. |
| Ein Bestellstatus lässt sich nicht wählen | Zulässige Folgestatus, deine Rechte und erforderliche Bestandsbuchungen prüfen. |

## Anmeldung oder Anmeldefaktor verloren

Bei lokalen Konten nutze die Passwortzurücksetzung, sofern der Mailversand eingerichtet ist. Für LDAP/SSO ist der Identitätsanbieter zuständig. Bei Verlust eines zweiten Faktors verwende einen noch unbenutzten Wiederherstellungscode und richte danach einen neuen Faktor ein. Fehlen alle Faktoren, wende dich an die Administration; privilegierte Konten werden durch das Serverteam über `jfctl` wiederhergestellt.

## Einen Fehler melden

Notiere Zeitpunkt, Modul, Aktion, aktive Abteilung und genaue Fehlermeldung. Beschreibe den erwarteten und tatsächlichen Zustand. Teile keine Passwörter, Codes, Sitzungscookies oder ungeschwärzte Mitgliederdaten in öffentlichen Issues. Frage eure Administration nach einem geeigneten Meldeweg.
