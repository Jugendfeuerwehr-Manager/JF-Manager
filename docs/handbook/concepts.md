# Grundlegende Konzepte

## Organisation, Abteilung und Gruppe

Die **Organisation** ist eure gesamte Installation. **Abteilungen** trennen fachliche Zuständigkeiten und Daten. Eine **Mitgliedergruppe** ordnet Personen für die Arbeit zusammen, etwa nach Alter oder Mannschaft. Eine Berechtigungsrolle legt dagegen fest, was ein angemeldetes Konto tun darf.

Prüfe vor dem Anlegen, Bearbeiten oder Exportieren immer die gewählte Abteilung. Der Umschalter begrenzt die Ansicht; er erteilt keine zusätzlichen Rechte. Organisationen ohne aktive Abteilung können organisationsweite Mitgliederlisten führen. Bei bestehenden Abteilungen gehört eine Liste genau einer Abteilung. Unklare Altlisten werden erst nach administrativer Klärung wieder freigegeben.

## Person und Benutzerkonto

Ein **Mitglied** oder **Elternkontakt** ist ein fachlicher Datensatz. Ein **Benutzerkonto** dient zur Anmeldung. Die Betreuungsliste im Dienstbuch verwendet aktive Benutzerkonten, die Mitgliederliste verwendet Mitgliedsdatensätze. Das ist auch dann unterschiedlich, wenn dieselbe Person in beiden Bereichen vorkommt. Ein Eintrag als Übungsleitung ersetzt keine Anwesenheitserfassung.

Verwende ein persönliches Konto. Geteilte Konten machen Änderungen und Verantwortlichkeiten schwer nachvollziehbar. Geplante Portalzugänge haben einen eigenen eingeschränkten Aufgabenbereich; sie sind keine Verwaltungsrollen.

## Rechte, Rollen und Herkunft

**Ansehen**, **Anlegen**, **Bearbeiten**, **Löschen** und Sonderaktionen wie Exportieren oder E-Mail-Versand sind getrennte Rechte. Die Standardrolle Jugendleiter erlaubt beispielsweise nicht automatisch Listenexport oder E-Mail-Versand. Rollen werden für eine Abteilung oder die Organisation zugewiesen. Mehrere Rollen addieren sich innerhalb ihres jeweiligen Bereichs.

Beispiel: Jugendleiter in Mitte plus Inventarverwaltung in Nord erlaubt Mitgliedereinsicht in Mitte und Materialverwaltung in Nord. Daraus entsteht kein Mitgliederschreibrecht in Nord. Organisationssicht allein ersetzt kein globales Fachrecht.

Eine Rolle kann **lokal**, durch **LDAP** oder **OIDC** stammen. Entfernst du nur die lokale Zuweisung, kann dieselbe externe Rolle weiterwirken. [Rollen zuweisen und prüfen](administrators/roles.md) erklärt Wirkungsvorschau und Herkunft. Die Standardrolle Systemadministration verwaltet Konten und Einstellungen; Fachaufgaben benötigen zusätzliche Rollen.

## Übung und Dienstbuch

Eine **Übung** enthält Planung: Gruppen, Stationen, Zeiten, Ausbilder und Materialbedarf. Ein **Dienst** dokumentiert den Termin und seine Anwesenheiten. Beim Veröffentlichen einer Übung entsteht der zugehörige Dienst. Entwürfe sind noch keine veröffentlichten Dienste.

| Zustand der Übung | Bedeutung für die Arbeit |
| --- | --- |
| Entwurf | Ablauf vorbereiten und prüfen |
| Veröffentlicht | Termin und Ablauf freigegeben; Dienstbuch verknüpft |
| Abgeschlossen | Durchführung beendet; Dokumentation bleibt erhalten |
| Abgesagt | Termin findet nicht statt; vorhandene Dokumentation bleibt erhalten |

Warnungen zu Material, Orten oder Ausbildern helfen bei der Planung. Materialbedarf **reserviert und bucht keinen Bestand**. Die tatsächliche Ausgabe erfolgt im Inventar. Bibliotheksbausteine werden beim Einfügen kopiert; spätere Bibliotheksänderungen ändern keine bestehende Übung. Innerhalb einer Rotation können Stationsinhalte dagegen absichtlich verknüpft sein.

## Speichern, Gleichzeitigkeit und Verbindung

Anwesenheitsstatus speichern sofort je Person. Der Übungsplaner sammelt Änderungen dagegen als Entwurf, bis du **Speichern** wählst. Achte auf Rückmeldungen und Versionskonflikte. Bei einem Konflikt zuerst den aktuellen Stand prüfen; eine erneute Auswahl oder Wirkungsvorschau ist eine bewusste Entscheidung.

Die Web-App benötigt eine Internetverbindung. Installation auf dem Startbildschirm macht sie nicht zu einer Offline-Datenbank. Fehlgeschlagene Änderungen werden nicht im Hintergrund für später gesammelt. Ausdrucke und Handouts sind Momentaufnahmen mit einem bestimmten Stand.

## Webadministration und Hostbetrieb

Fachliche Einstellungen, Rollen, SMTP, SSO und Sync liegen in der Weboberfläche. Domain, HTTPS, Infrastruktur, Schlüsselring, Installation, Sicherungen und Updates liegen beim Serverteam und werden über `jfctl` verwaltet. Der Web-Betriebsstatus zeigt Informationen an; er startet keine Hostbefehle.
