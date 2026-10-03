# JF-Manager: Gesamtplanung für Sicherheit, Rollen, Übungsplanung, Bedienung und Betrieb

Stand: 03.10.2026 · Verbindliche Planungs- und Übergabegrundlage für die Umsetzung

## 0. Wiederaufnahme: zuerst lesen

Dieses Dokument ersetzt die bisherigen Planentwürfe im Gespräch vollständig. Es ist zugleich Spezifikation, Aufgabenübersicht und laufendes Arbeitsjournal. Jede umsetzende Person und jeder Agent muss es vor Arbeitsbeginn lesen und während der Arbeit aktualisieren.

| Feld | Aktueller Stand |
| --- | --- |
| Letzter Checkpoint | 03.10.2026: SEC-01.5 `4db95c8`; SEC-01.6 korrigiert Mitgliederrechte, 76/76 gezielte Backendtests bestanden. |
| Aktuelles Paket | SEC-01.6: Mitgliederlisten, Statistik und Objektprüfung korrigiert. |
| Umsetzungsstatus | EXEC-01 abgeschlossen; SEC-01 in Arbeit. Vorbestehende Änderungen bleiben Ausgangsstand und zählen nicht als erledigte Roadmap-Pakete. |
| Branch bei Dateianlage | `main` |
| Gemeinsamer Umsetzungsbranch | `feat/security-roles-training-operations` |
| Branch bereits angelegt? | Ja, von `main` bei `a04fc88`; Ausgangsstand in `b20e36f`. |
| Letzter Roadmap-Commit | `4db95c8` (`SEC-01.5`); dieser Commit: `fix(SEC-01.6): scope member reads and writes to permitted departments`. |
| Ausgangsstand | 102 vorbestehende Dateien in `b20e36f` gesichert. Lokale Redis-Datei `dump.rdb` blieb unversioniert. Vorheriger Status: `/tmp/jf-manager-pre-roadmap-status.txt` (lokale Momentaufnahme). |
| Nächster konkreter Schritt | SEC-01.7: übrige Objektbeziehungen, eigene Listenfilter, Sonderaktionen und lokale Staff-Bypässe inventarisieren. |
| Laufende Prozesse dieses Planungsschritts | Keine. Bereits vorhandene lokale Dienste gehören nicht zu diesem Planungsschritt. |
| Maßgebliche Regeln | Abschnitt 5, insbesondere „Ein Branch, ein Commit je Teilschritt“ und „Persistenter Fortschritt“. |

**Vor jeder Fortsetzung:** Wiederaufnahmeübersicht, Paketstatus und letzte Journaleinträge lesen, anschließend tatsächlichen Git-Diff, Dateien und Testergebnisse abgleichen. Ein Dokumenteintrag allein ist kein Nachweis, dass Code vorhanden oder geprüft ist.

## 1. Ziel, verbindliche Entscheidungen und Ausgangslage

Die Anwendung wird für öffentlichen Internetbetrieb abgesichert, erhält ein verständliches Rollenmodell, eine verlässlichere Übungsplanung, eine moderne Oberfläche und vereinheitlichte Installations- und Betriebswerkzeuge. Vue, PrimeVue und Django bleiben die technische Grundlage.

### 1.1 Festgelegte Produktentscheidungen

- Öffentlicher Internetbetrieb mit sensiblen Mitgliederdaten und strikt getrennten Abteilungsrechten.
- Modernes, lebendiges Design; alle vorhandenen Module werden berücksichtigt.
- Bestehende Funktionen verbessern und gezielt ergänzen.
- Anpassbare Rollenvorlagen auf Basis von Django-Gruppen; fachliche Leitung, Fachmodule und Systemadministration getrennt.
- Leitungspersonen dürfen freigegebene Rollen innerhalb ihres Zuständigkeitsbereichs zuweisen.
- Mitgliederlisten gehören jeweils genau einer Abteilung.
- Cookie-Sitzungen und MFA für privilegierte Konten; bisherige Browser-JWT- und klassische Token-Anmeldung entfallen. Externe API-Programme müssen nach Nutzerangabe nicht weiter unterstützt werden.
- Übungsplanung umfasst Stationen, Rotation, Ausbilder und Materialbedarf. Ressourcenkonflikte erzeugen Warnungen, keine Reservierungen oder Inventarbuchungen.
- Fachliche Konfiguration erfolgt vollständig über die Weboberfläche. Installation, Updates, Backups und Restore erfolgen über eine Host-CLI.
- Unterstützte Produktionswege: Docker Compose und native Debian-13-Installation, letztere auch in Proxmox-LXC mit demselben Installationskern.
- HTTPS kann integriert oder über einen vorhandenen Reverse Proxy betrieben werden.
- Abschließend vollständige, bebilderte Dokumentation und README anhand der fertigen Anwendung.
- **Die gesamte Umsetzung erfolgt in einem gemeinsamen Feature-Branch. Jeder abgeschlossene Teilschritt erhält einen eigenen Commit mit aktualisiertem Fortschrittsstand.**

### 1.2 Bisherige Untersuchung und ihre Grenzen

Untersucht wurde der Arbeitsstand einschließlich bereits vorhandener, uncommitteter Änderungen. 51 ausgewählte Backendtests und 26 Frontendtests bestanden. Zusätzliche isolierte Prüfungen mit fiktiven Daten reproduzierten:

1. Schreibzugriff in einer nur lesbaren Abteilung bei fehlendem Abteilungsparameter: HTTP 200 ohne Parameter, HTTP 403 mit ausdrücklich gewählter Zielabteilung.
2. Gruppenanlage in einer nicht zugewiesenen Abteilung: HTTP 201.
3. Zugriff auf fremde Mitgliederdaten über Mitgliederlisten: HTTP 200 trotz eigener Abteilung als Filter.
4. Ungefilterte Übernahme von HTML aus Mitgliedernamen in E-Mail-Inhalte. Eine tatsächliche Browser-Codeausführung wurde nicht separat getestet.
5. Übernahme von Benutzereingaben als Excel-Formeln: Der fiktive Name `=1+1` wurde als Formelzelle gespeichert.

Weitere Codebefunde betreffen öffentliche Medien, Geheimnisspeicherung, OIDC, Bestandsbuchungen und Betriebswerkzeuge. Nicht jeder Codebefund wurde als vollständiger Angriff reproduziert.

Bei der Übungsplanung wurde festgestellt:

- Seriengenerierung löscht vorhandene Folgetermine und erzeugt sie neu.
- Ausbildungsbausteine werden dabei nicht übernommen.
- Monatswiederholungen können ihren ursprünglichen Tag verlieren.
- Planverschiebungen werden über einzelne parallele Anfragen gespeichert; Teilfehler können einen teilweise gespeicherten Plan hinterlassen.
- Überschneidungen können einen überraschenden automatischen Tausch auslösen.
- Eine integrierte Ausbilder- und Materialplanung fehlt.

Die visuelle Erstbewertung basiert auf vorhandenen Demo-Abbildungen und Quellcode. Ein vollständiger interaktiver Durchlauf steht aus, weil die laufende lokale Oberfläche beim Laden von Vue-Modulen scheiterte. Kein Angriffstest gegen eine öffentlich betriebene Installation und kein vollständiger Abhängigkeits- oder Penetrationstest wurden durchgeführt.

Die vorhandenen Tests liefen vor der Umsetzung der neuen Roadmap. Ihre Ergebnisse ersetzen keine späteren Paketabnahmen. Die zusätzlichen Auditprüfungen waren temporäre Prüfskripte; sie müssen als dauerhafte Regressionstests in das Repository übernommen werden.

### 1.3 Einstiegspunkte und Quellen

- Rechteprüfung: `backend/jf_manager_backend/permissions.py`, `backend/departments/mixins.py`.
- Gruppen, Mitglieder und Listen: `backend/members/api_serializers.py`, `backend/members/api/viewsets/`, `backend/members/api/serializers/list_serializers.py`.
- HTML und Exporte: `backend/members/services/email_service.py`, Mitglieder-/Listenexporte und `v-html`-Ausgaben im Frontend.
- Anmeldung und Geheimnisse: `backend/users/oidc_views.py`, `backend/users/auth_security.py`, `backend/jf_manager_backend/settings.py`, `backend/external_sync/models.py`.
- Übungsplanung: `backend/training/`, `frontend/src/stores/trainingPlanner.ts`, `frontend/src/components/training/organisms/SwimlaneEditor.vue`.
- Betrieb: `setup.sh`, `deploy.sh`, `scripts/backup.sh`, `scripts/restore.sh`, Compose-Dateien, Dockerfiles und `.github/workflows/`.

Fachliche Referenzen, geprüft während der Planung:

- [Django-Supportübersicht](https://www.djangoproject.com/download/)
- [OWASP: XSS Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [OWASP: HTML5 Security / Browser-Speicherung](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html)
- [Debian 13: Veröffentlichung](https://www.debian.org/News/2025/20250809)
- [Proxmox Community Scripts](https://github.com/community-scripts/ProxmoxVE)
- [Proxmox: Container-Dokumentation](https://github.com/proxmox/pve-docs/blob/master/pct.adoc)
- [Caddy: Automatic HTTPS](https://caddyserver.com/docs/automatic-https)

Versions- und Supportangaben beim tatsächlichen Implementierungsbeginn erneut prüfen.

## 2. Sicherheit, Rollen und Konfiguration

### 2.1 Sicherheitsarbeitspakete

**P0:** vor öffentlichem Produktiveinsatz erledigen. **P1:** vor Abschluss der Gesamtauslieferung erledigen. Diese Prioritäten gelten auch dann, wenn Design- oder Funktionspakete parallel vorbereitet werden.

| ID | Priorität | Befund und verbindlicher Lieferumfang |
| --- | --- | --- |
| SEC-01 | P0 | Reproduzierte Vermischung abteilungsbezogener Rechte: Rechte zentral nach Aktion und tatsächlicher Objektabteilung prüfen. Queryparameter dürfen Zugriffe nur einschränken. Rollen aus unterschiedlichen Abteilungen nicht zusammenführen. Vollqualifizierte Django-Permissions verwenden; unbekannte Aktionen standardmäßig verweigern. |
| SEC-02 | P0 | Reproduzierte Gruppenanlage in fremder Abteilung: Zielabteilungen und relationale Zuordnungen bei sämtlichen Schreibaktionen prüfen; insbesondere Gruppen, Ausbildung, Listen, Qualifikationen, Inventar und Bestellungen. Sammelaktionen dürfen keine unzulässigen Teiländerungen hinterlassen. |
| SEC-03 | P0 | Reproduzierter Zugriff auf fremde Mitglieder über globale Listen: Mitgliederlisten samt Einträgen, Exporten und Anhängen abteilungsbezogen machen. Gemischte Altlisten kontrolliert aufteilen. Mehrdeutige Zuordnungen und Anhänge bis zur Klärung für normale Nutzer sperren. |
| SEC-04 | P0 | Ungefilterte HTML-Übernahme und uneinheitliche `v-html`-Ausgaben: Textplatzhalter escapen; Rich Text serverseitig mit Allowlist und frontendseitig über eine gemeinsame DOMPurify-Komponente bereinigen. Regex-Bereinigung ersetzen. E-Mail-Vorschauen ohne Skriptausführung isolieren. Altinhalte ebenfalls sicher ausgeben und migrieren. |
| SEC-05 | P0 | Öffentliche Medien außerhalb des gesperrten Anhangpfads: Private Medien ausschließlich nach Objektberechtigung ausliefern. Öffentliche Branding-Dateien getrennt behandeln. Alte öffentliche Uploadpfade und Cachefreigaben beseitigen. Dateiinhalte, Anzahl und Gesamtgröße prüfen. |
| SEC-06 | P0 | Fest eingebauter Verschlüsselungsersatzschlüssel und unverschlüsselte Sync-Zugangsdaten: Ersatzschlüssel entfernen, Produktionsstart ohne gültigen Schlüssel verweigern und Sync-Zugangsdaten verschlüsseln. Umverschlüsselung und anschließende Rotation betroffener Zugangsdaten dokumentieren. |
| SEC-07 | P1 | JWTs in `localStorage`, nur lokaler Logout sowie OIDC-Codebefunde: Serverseitige Cookie-Sitzungen, CSRF-Schutz, Logout und MFA einführen. OIDC browsergebunden mit PKCE, atomarer Einmalverwendung und geprüften Endpunkten absichern. Keine personenbezogenen Diagnosedaten in Redirect-URLs. |
| SEC-08 | P1 | Reproduzierte Excel-Formelübernahme: Benutzereingaben ausdrücklich als Text schreiben; echte Zahlen und Datumswerte typisiert erhalten. Gemeinsame sichere Exportfunktion, Exportberechtigungen und Auditereignisse ergänzen. |
| SEC-09 | P1 | `Transaction.save()` bucht bei wiederholtem Speichern erneut; allgemeine Bestandsänderungen sind nicht durchgängig gesperrt: Bestandsbewegungen unveränderlich machen; Korrekturen über Gegenbuchungen. Konkurrenzschutz, atomare Buchungen und Idempotenz einführen. |
| SEC-10 | P1 | Lockdatei mit Django 5.0.14 und unvollständig geprüfte Betriebsgrundlagen: Unterstützte Django-Version, geprüfte Abhängigkeiten, sichere Produktionsvorgaben, Sicherheitsheader, Rate-Limits und automatisierte Betriebsprüfungen etablieren. |

Django 5.0 erhält keine Sicherheitsupdates mehr. Ziel ist die jeweils aktuelle Patchversion von Django 5.2 LTS; die Kompatibilität aller Abhängigkeiten muss vor dem Upgrade nachgewiesen werden.

#### Gemeinsame Sicherheitsverträge

- Organisationsweite Sichtbarkeit und fachliche Änderungsrechte getrennt behandeln. `can_access_all_departments` erweitert nur den Datenbereich.
- Bei gemeinsam zugeordneten Mitgliedern genügt Schreibrecht in einer zugehörigen Abteilung für gemeinsame Stammdaten. Abteilungszuordnungen ändern nur organisationsweit ausdrücklich autorisierte Administratoren.
- Verschachtelte Daten, etwa weitere Kinder eines Elternkontakts, nach Sichtbarkeit filtern.
- Aktionsrechte ausdrücklich abbilden: Abhaken verlangt Änderungsrechte, Exportieren Exportrechte und Versand Versandberechtigung.
- Authentifizierte private Downloads und Vorschauen erhalten `private, no-store`; direkte private Uploadpfade bleiben gesperrt. SVG/HTML nicht als aktive Vorschau ausliefern.
- Produktionsbetrieb erhält restriktive Sicherheitsheader und eine zunächst beobachtete, anschließend durchgesetzte CSP. TLS- und Proxy-Vertrauen ausdrücklich konfigurieren.
- Redis und Datenbank bleiben intern. Gemeinsame Caches für prozessübergreifende Limits verwenden.
- Sicherheitsprotokolle erfassen Akteur, Aktion, Objekt, Abteilung und Ergebnis, aber keine Geheimnisse oder vollständigen sensiblen Inhalte. Technischer Standard: 180 Tage konfigurierbare Aufbewahrung.

#### Listenmigration

- Neue Listen benötigen genau eine Abteilung; Mitglieder müssen zu dieser Abteilung gehören.
- Eindeutig zuordenbare Altlisten automatisch zuordnen, gemischte Listen pro Abteilung aufteilen und Checkstände erhalten.
- Mehrfachzugehörigkeiten, leere Listen, Beschreibungen und Anhänge benötigen eine explizite Zuordnung, wenn deren Sichtbarkeit nicht eindeutig ist.
- Ungeklärte Altbestände bleiben bis zur Zuordnung nur für die Migration durch Superuser sichtbar. Anhänge nicht automatisch an mehrere Abteilungen verteilen.

### 2.2 ROLE-01: Verständliche, ausgelieferte Rollen

Django-Gruppen bleiben die Quelle der Berechtigungen. Eine ergänzende Rollenbeschreibung enthält stabilen Vorlagenschlüssel, Anzeigename, Beschreibung, Vorlagenversion, zulässigen Geltungsbereich und Delegierbarkeit. Keine zweite unabhängige Rechteengine.

| Rolle | Standardbereich | Anfangsberechtigungen |
| --- | --- | --- |
| Jugendwart | Organisation | Mitglieder, Eltern, Gruppen, Listen, Dienstbuch, Ausbildung, Qualifikationen und Sonderaufgaben fachlich verwalten; fachliche Exporte; begrenzte Rollenzuweisung. |
| Abteilungsjugendwart | Zugewiesene Abteilung | Dieselben fachlichen Aufgaben innerhalb der eigenen Abteilung; begrenzte Rollenzuweisung. |
| Jugendleiter | Zugewiesene Abteilung | Mitglieder und erforderliche Kontakte lesen; Dienste, Anwesenheiten, Listen und Übungen bearbeiten; Qualifikationen lesen. Keine Benutzerverwaltung, Stammdatenlöschung oder Massenexporte. |
| Betreuer | Zugewiesene Abteilung | Veröffentlichte Übungen, Dienste und erforderliche Teilnehmerinformationen lesen; Anwesenheit erfassen. Keine Stammdatenbearbeitung oder Exporte. |
| Inventarverwaltung | Abteilung oder ausdrücklich Organisation | Artikel, Lagerorte, Ausgabe, Rücknahme, Gegenbuchungen und Inventarauswertungen verwalten. Nur erforderliche Mitgliederdaten sehen. |
| Bestellverwaltung | Abteilung oder ausdrücklich Organisation | Bestellungen, Status, Teilmengen und Wareneingänge bearbeiten; erforderliche Artikel-/Bestandsinformationen lesen. |
| E-Mail-Kommunikation | Abteilung oder ausdrücklich Organisation | Empfänger auswählen, Nachrichten verfassen, versenden und Versandhistorie im Zuständigkeitsbereich prüfen. Keine SMTP-/SSO-Konfiguration. |
| Ausbildungsplanung | Abteilung oder ausdrücklich Organisation | Übungen, Serien, Ressourcenplanung und abteilungseigene Vorlagen verwalten. |
| Bibliotheksredaktion | Organisation | Gemeinsam verfügbare Ausbildungsbausteine, Kategorien und Schlagwörter pflegen. |
| Qualifikationsverwaltung | Abteilung oder ausdrücklich Organisation | Nachweise, Gültigkeit und Sonderaufgaben bearbeiten; fachliche Auswertungen. |
| Systemadministration | Organisation | Konten, Rollendefinitionen, Integrationen, Sicherheit und Anwendungskonfiguration verwalten. Fachlicher Datenzugriff wird zusätzlich zugewiesen. |

Verbindliche Regeln:

- Fachmodule Inventar, Bestellungen und E-Mail werden separat ergänzt; Leitungsrollen erhalten sie nicht automatisch.
- Rollen werden additiv kombiniert, jeweils nur innerhalb ihres zugewiesenen Bereichs.
- `is_staff` allein gewährt keinen fachlichen Vollzugriff; es steuert den Django-Admin-Zugang. Superuser bleibt ein gesondertes Notfallkonto mit MFA.
- Endgültiges Löschen beziehungsweise Anonymisieren personenbezogener Daten ist eine gesonderte, initial nicht delegierbare Berechtigung.
- Normale Nutzer bearbeiten keine Rollenvorlagen. Systemadministratoren können Vorlagen ändern, duplizieren, umbenennen und archivieren.
- Installation legt Standardgruppen einmalig und idempotent an. Updates überschreiben keine kundenseitigen Anpassungen und erweitern bestehende Gruppen nicht stillschweigend.
- Vorlagenänderungen werden als Vergleich angeboten und ausdrücklich übernommen.
- Bestehende Gruppen nicht allein anhand gleicher Namen überschreiben; die Migration zeigt Zuordnungen und Rechteunterschiede. Staff-Konten nicht automatisch zu Vollzugriff migrieren.

### 2.3 ROLE-02: Einfache Zuweisung und sichere Delegation

Der normale Ablauf lautet: **Person auswählen → Bereich auswählen → Rolle auswählen → Wirkung prüfen → speichern**.

- Jugendwart darf Abteilungsjugendwarte und freigegebene untergeordnete Rollen zuweisen.
- Abteilungsjugendwart darf freigegebene Jugendleiter-, Betreuer- und Fachrollen seiner Abteilung zuweisen.
- Organisationsweite Rollen, Jugendwart und Systemadministration vergibt ausschließlich die Systemadministration.
- Delegierbare Fachrollen werden administrativ freigegeben; Änderungen an deren Berechtigungen erfordern eine erneute Freigabe.
- Keine Selbstbeförderung, Bearbeitung privilegierter Konten oder Ausweitung auf fremde Abteilungen.
- Technische Permission-Codenamen erscheinen nur in einer erweiterten Ansicht.
- „Warum darf diese Person das?“ zeigt Rolle, Bereich und Herkunft der Berechtigung.
- LDAP-/OIDC-Zuordnungen verwenden dieselben Rollen. Extern verwaltete Zuweisungen sind gekennzeichnet; Entfernen einer externen Zuordnung darf unabhängige lokale Zuweisungen nicht entfernen.

### 2.4 CFG-01: Vollständige fachliche Konfiguration im Interface

Ein Einrichtungsassistent führt durch Organisation, Abteilungen, erste Rollenzuweisungen, Standardwerte und optionale Integrationen.

| Über die Weboberfläche | Über Host-CLI beziehungsweise Umgebung |
| --- | --- |
| Organisation, Branding, Abteilungen, Rollen und Benutzer | Installationsmodus, Ports, Domain, Proxy-Vertrauen |
| Gruppen, Status, Eintragstypen, Qualifikationstypen | Datenbank-/Redis-Verbindung und Dateisystempfade |
| Dienstzeiten, Übungsstandards, Vorlagen | Django-Geheimnis und Verschlüsselungsschlüssel |
| Inventar-/Bestellstammdaten und Workflows | Betriebssystemdienste, Container und Releaseversion |
| SMTP, E-Mail-Vorlagen, LDAP, OIDC, Sync | TLS-Betriebsart, Backupziel und Backupentschlüsselung |
| Push-Aktivierung, VAPID-Einrichtung, Sicherheitsrichtlinien | Bootstrap-/Notfalladministration und Wiederherstellung |

- Für jedes Einstellungsfeld werden Speicherort, Berechtigung, Validierung und Wirksamkeitszeitpunkt festgelegt.
- DB-gestützte Einstellungen haben eine eindeutige Quelle. Zulässige Umgebungsüberschreibungen sind im Interface als gesperrt mit Herkunft sichtbar.
- Geheimnisse sind nur schreibbar, maskiert und verschlüsselt gespeichert.
- Verbindungstests verändern keine produktiven Daten; E-Mail-Testversand ist eine ausdrückliche Aktion.
- Nach der Einrichtung ist für normale Administration kein Django-Admin erforderlich.

#### Sitzungen und MFA

- Django-Sitzungen über sichere, hostgebundene Cookies mit `Secure`, `HttpOnly` und `SameSite=Lax`; Frontend und API unter derselben Herkunft betreiben.
- CSRF-Prüfung für alle zustandsändernden Browseranfragen einschließlich Login und Logout.
- Schnittstellen für Sitzungsstatus, Login, MFA-Verifikation und serverseitigen Logout; Browserantworten enthalten keine Zugangstokens.
- Standard: 30 Minuten Inaktivität und zwölf Stunden Maximaldauer, innerhalb serverseitiger Grenzen administrativ konfigurierbar. Ablauf vorher sichtbar ankündigen.
- Sicherheitsänderungen verlangen eine höchstens fünf Minuten alte erneute Bestätigung.
- TOTP und einmalige, gehashte Wiederherstellungscodes; MFA verpflichtend für Leitungsrollen mit Delegation und administrativ privilegierte Konten. Für sonstige Benutzer optional.
- Lokaler Login, LDAP und Django-Admin unterliegen denselben Regeln. Geprüfte SSO-MFA kann bei ausdrücklich konfiguriertem Provider-Nachweis anerkannt werden.
- Beim gemeinsamen Backend-/Frontendwechsel alte JWT-/Token-Zugänge abschalten und bestehende Sitzungen widerrufen.

## 3. Übungsplanung, Design und übrige Fachmodule

### 3.1 TRAIN-01: Verlässliche Planbearbeitung

- Gemeinsamer Ablauf: **Termin anlegen → Inhalte planen → Ressourcen prüfen → veröffentlichen → durchführen → nachbereiten**.
- Status: Entwurf, veröffentlicht, abgeschlossen, abgesagt.
- Der Plan wird als zusammenhängender Entwurf bearbeitet. Eine atomare Speicheraktion übernimmt Bausteine, Zeiten, Gruppen und Ressourcenzuordnungen gemeinsam.
- Optimistische Versionsprüfung verhindert stilles Überschreiben. Ein Konflikt erhält lokale Änderungen und zeigt die abweichende Serverversion.
- Verschieben und Größenänderung sind per Drag-and-drop, Tastatur und Formular möglich.
- Kein automatischer Tausch allein durch Überlappung. „Tauschen“ und „Nachfolgende verschieben“ sind ausdrückliche Aktionen mit Vorschau.
- Rückgängig/Wiederholen gilt für noch nicht gespeicherte Planänderungen; Verlassen warnt vor ungespeicherten Änderungen.
- Zeiten werden serverseitig validiert: positive Dauer, keine negativen Offsets und keine Blöcke außerhalb des Terminrahmens.
- Mehrtägige Übungen werden zunächst als mehrere Termine geplant; Ende muss am selben Tag nach Beginn liegen.

### 3.2 TRAIN-02: Stationen, Rotation und Ressourcen

- Stationen besitzen Titel, Ort, Dauer, Lernziel, Ablauf, Sicherheitshinweise und Materialbedarf.
- Gruppen können Stationen in einer erzeugten Rotation durchlaufen; Wechselzeiten und Pausen sind eigene Planbestandteile.
- Rotationsassistent fragt Gruppen, Stationen, Reihenfolge, Stationsdauer und Wechselzeit ab und zeigt den vollständigen Ablauf vor Übernahme.
- Ungleiche Gruppen-/Stationszahlen erzeugen ausdrücklich gekennzeichnete freie Runden statt stiller Mehrfachbelegung.
- Ausbilder werden Bausteinen zugeordnet. Materialbedarf verweist optional auf Inventarartikel/Varianten und Mengen; Freitextbedarf bleibt möglich.
- Konfliktprüfung erkennt überlappende Gruppen, Ausbilder, gepflegte Ressourcenorte und rechnerischen Materialmangel.
- Konflikte sind Planungswarnungen. Veröffentlichung trotz Warnungen verlangt eine dokumentierte Begründung; ungültige Zeit- oder Rechteangaben blockieren.
- Materialbedarf verändert weder Bestand noch Verfügbarkeit. Tatsächliche Ausgabe erfolgt weiterhin im Inventar.
- Fremde, nicht sichtbare Belegungen dürfen nur als anonymisierter Konflikt erscheinen.

### 3.3 TRAIN-03: Vorlagen und sichere Serien

- Ganze Übungen sowie einzelne Bausteine als Vorlagen speichern und kopieren.
- Übernahme erzeugt einen eigenständigen Stand; spätere Bibliotheksänderungen verändern geplante Übungen nicht automatisch.
- Serientermine besitzen eine stabile Serienidentität und einen ursprünglichen Terminbezug.
- Generierung ergänzt fehlende Termine, statt bestehende zu löschen.
- Änderungsoptionen: „dieser Termin“ und „dieser und folgende“. Abweichende Einzeltermine werden erkannt und standardmäßig erhalten.
- Vergangene/abgeschlossene Termine und ihre Anwesenheiten bleiben unverändert.
- Monatsserien behalten den ursprünglichen Monatstag; bei fehlendem Tag den Monatsletzten verwenden, im Folgemonat wieder den ursprünglichen Tag.
- Vorschau zeigt neue, geänderte, ausgelassene und konfliktbehaftete Termine.
- Standardgrenze: höchstens 200 Vorkommen je Aktion und höchstens 24 Monate Vorschau.
- Dienstbuchverknüpfung bleibt stabil. Entwürfe erzeugen keinen regulären Dienst; Veröffentlichung legt ihn an oder aktualisiert ihn. Nach Beginn erfolgen Änderungen an dokumentierten Diensten nur ausdrücklich.
- Bestehende verknüpfte Übungen werden bei Migration veröffentlicht übernommen; Altserien werden nicht automatisch neu erzeugt.

### 3.4 TRAIN-04: Durchführung und Nachbereitung

- Mobile Ansicht zeigt aktuellen/nächsten Block, Gruppen, Ausbilder und Materialien.
- Gedrucktes Handout und PDF enthalten Ablauf, Stationskarten, Materialliste und Versionsstand.
- Abschluss erfasst kurze Reflexion, tatsächliche Dauer und Verbesserungshinweise.
- Anwesenheiten verbleiben im Dienstbuch; Planzeit und tatsächliche Dauer werden nicht verwechselt.
- Kein neuer Offline-Schreibmodus: fehlende Verbindung und ungespeicherte Änderungen bleiben sichtbar.

### 3.5 DES-01: Gemeinsames Designsystem

- Heller Grund `#F5F7FA`, weiße Inhaltsflächen, Schrift `#172033`, Feuerwehrrot `#B91C1C`.
- Einheitliche Typografie, 8-Pixel-Abstandssystem, moderate Rundungen, zurückhaltende Schatten, Tabellen, Formulare, Statusanzeigen und Fehlerzustände.
- Zustände zusätzlich durch Text/Symbole kennzeichnen; Farben allein reichen nicht.
- Bestehenden Dunkelmodus mitpflegen; lokale Schriften oder Systemschriften verwenden.
- Dauerhafte Desktopnavigation; vollständige mobile Modulnavigation und sichtbarer Abteilungskontext.
- Mindestens 44 × 44 Pixel große Touchflächen, Tastaturbedienung, sichtbarer Fokus, reduzierte Animationen.
- Referenzansichten: Dashboard, Mitgliederliste, Formular, Übungsplaner und mobile Anwesenheit.

Die vorhandenen Demoansichten zeigen viel gleichgewichtige weiße Fläche, wenig visuelle Hierarchie, einen Inventar-Platzhalter und ein wenig aussagekräftiges Diagramm. Die mobile Abteilungsanzeige ist abgeschnitten. Diese Punkte werden gezielt korrigiert.

### 3.6 Weitere Modulverbesserungen

| ID | Bereich | Lieferumfang |
| --- | --- | --- |
| UX-01 | Dashboard | Berechtigungsabhängige nächste Aufgaben, kommende Dienste, offene Bestellungen, ablaufende Qualifikationen und Fehlerzustände; keine Platzhalterkennzahlen. Kennzahlen öffnen passende gefilterte Ansichten. |
| UX-02 | Mitglieder/Eltern/Gruppen | Klar gegliederte Profile, Dublettenwarnung, passende Kontaktaktionen, gespeicherte Filter/Spalten pro Benutzer und Abteilung; sensible Daten nur bedarfsgerecht laden. „AnonymousUser“ und inaktive Konten aus fachlichen Personenauswahlen entfernen. |
| UX-03 | Listen/Einträge | Fortschritt, ausdrückliche Checkzustände, Konfliktschutz und Vorschau von Sammelaktionen. Mitgliederereignisse vom Sicherheitsprotokoll unterscheiden. |
| UX-04 | Dienstbuch | Mobile Erfassung, verständliche Statusbezeichnungen, offene Personen und sichtbarer Speicher-/Synchronisationszustand. Bestehende Einzeländerungen und Konfliktprüfung erhalten. |
| UX-05 | Inventar/Bestellungen | Verfügbar, ausgeliehen und bestellt unterscheiden; geführte Ausgabe/Rücknahme, manuelle Scanalternative, Teilmengen und Statusverlauf. Doppelbuchungen verhindern. |
| UX-06 | Qualifikationen | Ablaufansichten für 30/60/90 Tage, fehlende Nachweise, Verlängerung und Historie. |
| UX-07 | E-Mail | Empfängerprüfung, sichere Vorschau, Hintergrundversand, Teilergebnisse und Wiederholung nur fehlgeschlagener Zustellungen. Unterschiedliche personalisierte Nachrichten nicht allein wegen derselben Empfängeradresse zusammenlegen. |
| UX-08 | Sync/Profil | Änderungsvorschau, Konflikte und Laufhistorie; Sitzungen, MFA und gerätebezogene Push-Einstellungen. |

#### Gemeinsame Bedienregeln und Schnittstellen

- Eine klar erkennbare Hauptaktion pro Ansicht; sekundäre und destruktive Aktionen unterscheiden.
- Fehler direkt am betroffenen Feld anzeigen und Eingaben erhalten. Ungespeicherte Änderungen beim Verlassen schützen.
- Wiederholen, leere Ergebnisse, fehlende Rechte und technische Fehler erhalten eigene Zustände. Fehlgeschlagene Änderungen niemals als gespeichert darstellen.
- Sensible Formularentwürfe nicht dauerhaft im Browser speichern. Bestehende Datensätze erhalten stabile Direktlinks.
- Effektive Fähigkeiten je Bereich für die UI bereitstellen; Serverrechte bleiben maßgeblich.
- Dashboard-Zusammenfassungen statt vollständiger Personenlisten nur zum Zählen abrufen.
- Benutzerbezogene Ansichtspräferenzen ohne personenbezogene Suchinhalte speichern.
- Versionskennungen für konkurrierende Änderungen und verständliche Konfliktantworten bereitstellen.
- Auftragsstatus für Versand und Synchronisation sowie Idempotenzschlüssel für Versand, Bestellannahme und Bestandsbuchung einführen.
- Unveränderlicher Änderungs-/Sicherheitsverlauf mit eigener Leseberechtigung.
- Sämtliche Stores bei Logout leeren. Abteilungswechsel invalidiert laufende Anfragen; verspätete Antworten dürfen einen gewechselten Benutzer-/Abteilungskontext nicht überschreiben.

## 4. Installation und einheitlicher Betrieb

### 4.1 OPS-01: Zwei Betriebswege, ein Installationskern

**Docker Compose:** offizieller Produktionsweg mit vorgebauten, versionsgebundenen Images und Compose V2.

**Debian 13 nativ:** Anwendung in einer Python-Umgebung, PostgreSQL, Redis, Webserver und Worker als systemd-Dienste.

**Proxmox-LXC:** dünne Host-Komponente erzeugt einen unprivilegierten Debian-13-Container und führt darin exakt den nativen Installationskern aus. Keine separate Anwendungsinstallation und kein Docker im LXC.

Referenzplattformen sind Linux/Debian 13 auf amd64 sowie Proxmox VE 9.x. Weitere Architekturen werden erst nach eigener Installations- und Restoreprüfung zugesichert. Debian 13 ist die festgelegte native Basis.

Die Bedienung orientiert sich an Standard-/Expertenmodus und anschließender Verwaltung der Proxmox Community Scripts. Eine Veröffentlichung im dortigen Katalog ist keine Voraussetzung dieses Projekts.

### 4.2 OPS-02: Installationsassistent

Vor Änderungen werden alle erforderlichen Angaben erhoben und zusammengefasst:

- Installation oder Wiederherstellung; Betriebsmodus und Releaseversion.
- Domain, Zeitzone, integriertes HTTPS oder vorhandener Reverse Proxy.
- Daten-/Backupverzeichnis, Zeitplan, Aufbewahrung und Backupverschlüsselung.
- Bootstrap-Administrationskonto.
- Bei LXC zusätzlich CT-ID, Hostname, Storage, CPU, RAM, Plattengröße, Bridge, IP/DHCP, Gateway und DNS.

Standardmodus zeigt sinnvolle Vorgaben; Expertenmodus weitere technische Optionen. Ungültige Plattformen, belegte Ports und unzureichender Speicher werden vor Installation erkannt.

- Integriertes HTTPS über Caddy; alternativ ausdrücklich konfigurierte vertrauenswürdige Proxyadressen.
- Geheimnisse werden generiert oder verdeckt eingegeben und nicht protokolliert.
- Installation ist wiederholbar und besitzt prüfbare Schritte mit Wiederaufnahme.
- Bootstrap auf einem Proxmox-Host installiert dort keine Anwendungsdienste.
- Fachliche Einrichtung folgt im Webassistenten; Antworten werden nicht doppelt abgefragt.
- Automatisierung über dieselben Parameter und eine geschützte Antwortdatei; keine Geheimnisse in Prozessargumenten.

### 4.3 OPS-03: Verwaltungsbefehl `jfctl`

`jfctl` öffnet ein verständliches Menü. Unterbefehle erlauben Skriptbetrieb:

```text
jfctl install
jfctl status
jfctl doctor
jfctl start | stop | restart
jfctl logs
jfctl update --version <version>
jfctl backup create | list | verify
jfctl restore <backup-id>
jfctl config
jfctl admin bootstrap | recover
```

- Ein gemeinsamer CLI-Kern mit Compose- und systemd-Adaptern.
- Funktioniert auch bei gestoppter oder defekter Webanwendung.
- Django-Management-Commands übernehmen fachliche Wartung; die Host-CLI orchestriert Infrastruktur.
- Kein Docker-Socket und keine Root-Steuerung in der Webanwendung.
- Weboberfläche zeigt Betriebsstatus und letzte Sicherung lesend.
- Sperren verhindern parallele Updates/Restores. Rückgabecodes und bereinigte Logs sind eindeutig.
- Kein unkontrolliertes `git pull` oder Build beliebiger Branches auf Produktionssystemen.
- Releasepakete und Images besitzen prüfbare Herkunft, Manifest und feste Versionen.

### 4.4 OPS-04: Backup, Restore und Updates

Die heutigen Skripte sichern lediglich PostgreSQL. Zusätzlich können Pipelinefehler übersehen werden; Restore startet nach einer Wartezeit statt ausdrücklicher Zustimmung. Der bisher als Rollback bezeichnete Fehlerpfad stoppt lediglich Container. Diese Abläufe werden ersetzt.

#### Backup

- Verschlüsseltes Restic-Repository mit konsistentem Datenbankdump, Medien, notwendiger Konfiguration, Anwendungsschlüsseln und Versionsmanifest.
- Backup-Passwort getrennt vom Repository aufbewahren; Wiederherstellung auf neuem Host muss möglich sein.
- Kurzes Wartungsfenster stoppt Schreibaktionen und Worker für einen konsistenten Sicherungsstand.
- Fehlgeschlagene Dumps oder unvollständige Medienkopien erzeugen keinen erfolgreichen Backupstatus.
- Standardaufbewahrung: sieben tägliche, vier wöchentliche und sechs monatliche Sicherungen.
- Aktive Sitzungen werden bei Restore verworfen; wartende Versand-/Sync-Aufträge nicht ungeprüft erneut ausgeführt.

#### Restore

- Erst Integrität, Entschlüsselung, Versionskompatibilität und freien Speicher prüfen.
- Zielinstallation und Datenersetzung ausdrücklich bestätigen; kein Countdown als Zustimmung.
- Vorhandenen Zustand zusätzlich sichern.
- Wiederherstellung zunächst vorbereiten und prüfen, dann aktivieren.
- Docker und native Installation verwenden dasselbe logische Backupformat.
- Automatisierte Wiederherstellungsprobe auf leerem Zielsystem ist verpflichtend.

#### Update

1. Zielversion und Kompatibilität prüfen.
2. Artefakte laden und verifizieren.
3. Wartungsmodus und vollständiges Backup.
4. Migrationen und Releasewechsel.
5. Anwendung, Datenbank, Worker und zentrale Funktionen prüfen.
6. Erst danach freigeben.

Ein Rollback berücksichtigt Anwendung **und** Datenbankschema. Nach inkompatiblen Migrationen genügt kein Imagewechsel; erforderlichenfalls wird der gesicherte Zustand wiederhergestellt. Automatische Wiederherstellung erfolgt nur vor Wiederfreigabe und ohne inzwischen angenommene Nutzerschreibvorgänge.

### 4.5 OPS-05: Installationsvarianten konsolidieren

- Alte Portainer-, Synology-, Compose-V1- und sonstige eigenständige Produktionsanleitungen aus der aktiven Navigation entfernen.
- Bestehende Installationen über eine dokumentierte Migration zu einem der unterstützten Wege führen.
- Alte URLs/Dokumente erhalten einen kurzen Verweis auf Nachfolge und Migration.
- Entwicklungsanleitungen bleiben als Entwicklung gekennzeichnet.
- PostgreSQL wird für beide Produktionswege vereinheitlicht; bestehende ältere Datenbankversionen über geprüften logischen Export/Import migrieren.

## 5. Agent-Arbeit, Prüfungen und vollständige Dokumentation

### 5.1 EXEC-01: Ein Branch, ein Commit je Teilschritt

Diese Regeln sind verbindlicher Teil des Nutzerauftrags und gelten für alle Pakete:

1. **Ein gemeinsamer Umsetzungsbranch:** `feat/security-roles-training-operations`. Vor der ersten Implementierungsänderung von der geprüften Ausgangsbasis anlegen. Existiert er bereits, seinen Stand prüfen und weiterverwenden. Alle Roadmap-Änderungen einschließlich Tests, Migrationen, Dokumentation und Fortschrittsjournal werden dort integriert. Nicht auf `main` implementieren und keine getrennten Feature-Branches je Paket anlegen.
2. **Ausgangsstand schützen:** Vor dem Branchwechsel den vorhandenen Git-Status und die uncommittierten Änderungen erfassen und sichern. Nichts zurücksetzen, verwerfen oder pauschal stashen. Vorhandene Änderungen nicht ungeprüft als eigene Arbeit committen. Falls sie Voraussetzung eines Pakets sind, deren Herkunft und kontrollierte Übernahme dokumentieren.
3. **Planungs-Commit zuerst:** Die bereits angelegte Planungsdatei separat auf dem Umsetzungsbranch committen. Danach die verpflichtenden Arbeitsregeln in einer Repository-`AGENTS.md` verankern, damit spätere Agents diesen Plan beim Einstieg finden.
4. **Pakete in kleine Teilschritte zerlegen:** Vor Paketbeginn eine geordnete Checkliste mit stabilen IDs wie `SEC-01.1`, `SEC-01.2` anlegen. Ein Teilschritt ist eine nachvollziehbare logische Änderung, etwa ein Regressionstest, die zugehörige Korrektur, eine Migration oder ein abgegrenzter UI-Ablauf.
5. **Eigener Commit je abgeschlossenem Teilschritt:** Änderungen explizit nach Dateien oder Hunks stagen, Staged-Diff prüfen und passende Tests ausführen. Kein pauschales `git add .` über den vorhandenen Arbeitsstand. Keine Sammelcommits über mehrere unabhängige Teilschritte oder Pakete.
6. **Fortschritt im selben Commit:** Jeder Teilschritt-Commit enthält den zugehörigen Journal-/Statusstand und gegebenenfalls aktualisierte technische Dokumentation. Ergebnisse ehrlich als bestanden, fehlgeschlagen oder nicht ausgeführt markieren.
7. **Commitnamen mit Bezug:** Beispielsweise `test(SEC-01.1): cover cross-department role leakage`, `fix(SEC-01.2): enforce object-scoped permissions` oder `docs(DOC-01.3): illustrate training workflow`.
8. **Commitbezug ohne Endlosschleife:** Im Journal kann für den aktuellen Eintrag `dieser Commit: <Commit-Betreff>` stehen; dessen Hash wird aus Git ermittelt oder im nächsten Checkpoint ergänzt. Nicht allein zur Eintragung des eigenen Hashes wiederholt amendieren.
9. **Unterbrechungen sichern:** Bei notwendiger Übergabe mit unfertigem Code einen klar bezeichneten WIP-Checkpoint-Commit erstellen, sofern die eigenen Änderungen sicher abgrenzbar sind. Offene Tests und Fehler dokumentieren; Paket/Teilschritt bleibt „in Arbeit“. Andernfalls uncommittierte Dateien und sicheren Wiederaufnahmeweg exakt festhalten.
10. **Historie erhalten:** Fertige Teilschritt-Commits nicht zusammenquetschen oder umschreiben. Korrekturen erhalten neue Commits. Kein Force-Push, Merge nach `main`, Release oder Deployment allein aufgrund dieses Plans.
11. **Git-Operationen koordinieren:** Bei parallelen Agents übernimmt ein Integrationsagent Staging und Commits. Keine konkurrierenden Git-Schreiboperationen im gemeinsamen Checkout. Dateiverantwortung pro Paket vorher abgrenzen; jeder Teilschritt bleibt ein eigener Integrationscommit auf demselben Branch.

Die Vorgabe „ein Commit je Teilschritt“ bedeutet nicht „ein Commit erst am Ende eines großen Pakets“. Größere Pakete müssen mehrere logisch getrennte, wiederaufnehmbare Commits enthalten.

### 5.2 Persistenter Fortschritt ist Teil der Umsetzung

Eine ergänzende Repository-Anweisung in `AGENTS.md` muss jeden implementierenden Agent verpflichten, dieses Dokument und seinen Paketstatus vor Arbeitsbeginn zu lesen. Das Anlegen dieser Anweisung gehört zu EXEC-01 und ist noch offen.

Für jedes Paket bei Übernahme unter Abschnitt 6 einen ausgefüllten Detailblock anlegen:

```text
ID und Titel:
Status: offen | in Arbeit | blockiert | in Prüfung | abgeschlossen
Verantwortlicher Agent:
Abhängigkeiten:
Ziel und Abnahmekriterien:
Teilschritte mit stabilen IDs:
Letzter dauerhafter Checkpoint:
Branch:
Geänderte Dateien / Commit-Bezug:
Umgesetzte Teilschritte:
Ausgeführte Prüfungen mit Ergebnis:
Offene Fehler / Risiken:
Laufende Prozesse und sichere Fortsetzung:
Nächster konkreter Schritt:
```

#### Verbindlicher Arbeitsrhythmus

- Vor der ersten Änderung Paket übernehmen, Ausgangsstand, Abhängigkeiten und Teilschritte eintragen.
- Nach jedem abgeschlossenen Teilschritt aktualisieren, spätestens nach zehn Minuten aktiver Arbeit. Dokumentieren also auch während der eigentlichen Implementierung, nicht erst beim Commit oder Abschluss.
- Vor längeren Tests, Migrationen und riskanten Schritten einen Checkpoint schreiben; Ergebnis anschließend ergänzen.
- Vor Übergabe, Kontextkompaktierung oder absehbarem Tokenende aktuelle Änderungen, offene Prüfungen und nächsten Schritt sichern.
- Unterbrechungen können unvermittelt eintreten; deshalb muss bereits jeder reguläre Zwischenstand wiederaufnehmbar sein.
- „Implementiert, ungetestet“ bleibt ausdrücklich unvollständig.
- Neue Agents gleichen Dokument, Git-Diff und tatsächliche Dateien ab; Statusbehauptungen ersetzen keine Prüfung.
- Keine Passwörter, Token oder personenbezogenen Echtdaten im Arbeitsjournal.
- Bei paralleler Arbeit besitzt jedes Paket genau einen Bearbeiter; die Gesamtstatusübersicht pflegt der Integrationsagent.
- Abgeschlossen erst nach erfüllter Abnahme, Tests, Migration, Dokumentation und Commit aller zugehörigen Teilschritte.

Das fortlaufende Journal in Abschnitt 7 enthält Zeit, Paket-/Teilschritt-ID, Änderung, Prüfergebnis, Commitbezug und nächsten Schritt. Die Wiederaufnahmeübersicht am Dokumentanfang muss den aktuellen Zustand knapp wiedergeben.

### 5.3 Umsetzungsreihenfolge und Abhängigkeiten

| Etappe | Pakete | Ergebnis |
| --- | --- | --- |
| 0 | EXEC-01 | Persistenter Plan, gesicherter Ausgangsstand, gemeinsamer Branch, Teilschritt-Commits, Agent-Regeln und reproduzierbare Testumgebung. |
| 1 | SEC-01–06, ROLE-01/02 | Zugriffslücken geschlossen, Rollenmodell und sichere Datenmigration vorbereitet. |
| 2 | SEC-07–10, CFG-01 | Anmeldung, Betriebsgrundlagen und eindeutige Konfigurationsschnittstellen. |
| 3 | DES-01, TRAIN-01–04 | Gemeinsames Designsystem und zuverlässige erweiterte Übungsplanung. |
| 4 | UX-01–08 | Übrige Module auf dieselben Rechte-, Design- und Bedienregeln bringen. |
| 5 | OPS-01–05 | Beide Installationswege, Betriebs-CLI, Migration und Restore nachgewiesen. |
| 6 | DOC-01, Gesamtabnahme | Vollständige bebilderte Dokumentation und freigabefähiges Gesamtprodukt. |

Unabhängige Pakete können parallel umgesetzt werden, sobald gemeinsame Rechte-, API- und Migrationsverträge feststehen. P0-Sicherheitskorrekturen warten nicht auf das Redesign. ROLE-01/02 bauen auf SEC-01/02 auf; private Medien und sicheres HTML sind Voraussetzung für die neuen Trainings-/E-Mail-Ansichten. OPS-04 benötigt die Schlüssel-/Konfigurationsverträge aus SEC-06 und CFG-01. DOC-01 folgt nach fachlicher und visueller Fertigstellung aller Features.

### 5.4 Prüfplan

#### Rechte und Rollen

- Alle Standardrollen einzeln und kombiniert testen.
- Anonyme Benutzer, Leser, Bearbeiter, unterschiedliche Rechte derselben Person in A/B, Staff ohne Vollzugriff und Superuser berücksichtigen.
- Fehlende/manipulierte Abteilungsparameter, verschachtelte Daten und Direktzugriffe prüfen; je Modul Listen-, Detail-, Schreib-, Sammel-, Export- und Downloadzugriffe abdecken.
- Delegation, Selbstbeförderung, geänderte Vorlagen und LDAP-/OIDC-Entzug testen.
- Seed mehrfach ausführen: keine Duplikate, keine Überschreibung angepasster Gruppen.

#### Sicherheit und Datenintegrität

- Die fünf reproduzierten Auditbefunde erhalten dauerhafte Regressionstests.
- XSS-Testdaten in Namen, Notizen, Signaturen, Vorlagen und Ausbildungsinhalten bleiben in jeder Ausgabe ungefährlich.
- Private Dateien sind anonym, abteilungsfremd und nach Rechteentzug nicht zugänglich.
- Logout, Sitzungsablauf, CSRF, MFA-Replay, Wiederherstellungscodes und OIDC-Browserbindung testen.
- XLSX-Testeingaben bleiben Text; vorhandene fachliche Zahlen bleiben Zahlen.
- PostgreSQL-Konkurrenz- und Wiederholungsprüfungen verhindern Doppelversand, Doppelbuchung und verlorene Änderungen.

#### Übungsplanung

- Atomare Speicherung bei Teilfehlern, konkurrierende Änderungen und Erhalt lokaler Entwürfe.
- Gruppen-/Ausbilderkonflikte, gemeinschaftliche Blöcke, Materialmangel und fremde Ressourcen.
- Rotation mit gleichen/ungleichen Anzahlen sowie Pausen und Wechselzeiten.
- Monatsende, Schaltjahr, Sommerzeit, Serienausnahmen und wiederholte Generierung.
- Kein Verlust bestehender Bausteine, Medien, Dienste oder Anwesenheiten.
- Tastatur-, Touch- und Druckbedienung.

#### Betrieb

- Neuinstallation und Wiederholung auf Docker, Debian 13 und echtem Proxmox-LXC.
- Integriertes HTTPS und vorhandener Proxy.
- Abgebrochene Installation, fehlgeschlagenes Update, volle Platte und beschädigtes Backup.
- Restore auf neuem Host sowie Wechsel zwischen Docker und nativ.
- Fehlende Schlüssel, falsches Backup-Passwort und inkompatible Version müssen vor Datenersetzung auffallen.
- Ohne echten Proxmox-Test bleibt dessen Abnahme offen; simulierte Tests reichen nicht aus.

#### Produktübergreifend

- Bestehende und neue Sicherheitsregressionen; alle erforderlichen Build-/Typprüfungen.
- Fiktive Daten für alle Module und zwei Abteilungen; zusätzliche große Datensätze für Suche/Pagination. Keine echten Versand- oder Sync-Ziele.
- Desktop und mobile Breiten 360/390/768/1440 Pixel, Dunkelmodus, Tastatur und 200 Prozent Zoom.
- Netzfehler, fehlende Rechte und echte Leerzustände unterscheiden.
- Jeder Kernablauf erhält Prüfungen für Erfolg, fehlende Rechte, Validierungsfehler, Netzfehler und relevante konkurrierende Änderungen.
- Fehler beim Laden einer Route zeigen eine Wiederherstellungsansicht statt einer leeren Seite.

### 5.5 DOC-01: Dokumentation nach Fertigstellung aller Features

Während der Entwicklung werden technische Änderungen fortlaufend dokumentiert. Nach Funktionsabschluss folgt eine vollständige redaktionelle und visuelle Überarbeitung:

- **README:** Nutzen, aktuelle Screenshots, wichtigste Module und genau die unterstützten Installationswege.
- **Bebildertes Benutzerhandbuch:** alle Module, typische Arbeitsabläufe, mobile Bedienung und Fehlerbehebung.
- **Rollenhandbuch:** Rollenübersicht, Kombinationen, Delegation, Anpassung und nachvollziehbare Beispiele.
- **Übungsplanungs-Handbuch:** Stationen, Rotation, Ressourcen, Serien, Veröffentlichung, Durchführung und Handouts.
- **Administrationshandbuch:** Einrichtung, sämtliche UI-Einstellungen, SSO, MFA, Sync und Sicherheitsprotokolle.
- **Betriebshandbuch:** Installationsassistent, CLI, Updates, Backup, Restore, Migration und Notfallverfahren.
- **Entwicklungsdokumentation:** Architektur, Berechtigungsverträge, API, Migrationen, Tests und Agent-Wiederaufnahme.

Alle Bilder stammen aus der fertigen Anwendung mit reproduzierbaren fiktiven Daten. Screenshots erhalten Aufgabenbezug, Bildunterschriften und Alternativtexte. Veraltete Abbildungen und widersprüchliche Anleitungen werden ersetzt. Handbuchabläufe werden anhand der tatsächlichen Oberfläche nachvollzogen; Links und Befehle werden überprüft.

### 5.6 Gesamtabschluss

Alle Pakete sind abgenommen, offene Einschränkungen ausdrücklich dokumentiert, beide Betriebswege geprüft, Wiederherstellung nachgewiesen und sämtliche Handbuchabläufe nachvollzogen. Alle Teilschritte besitzen eigene Commits auf dem gemeinsamen Umsetzungsbranch. Das Journal enthält den finalen Prüfstand und gegebenenfalls verbleibende Betriebsgrenzen.

Eine erfolgreiche Einzelprüfung gilt nicht als vollständige Sicherheitsfreigabe. Zusammenführung nach `main`, Veröffentlichung und Produktivdeployment sind gesonderte Schritte; diese Planungsdatei löst sie nicht automatisch aus.

## 6. Lebender Paketstatus

Die Tabelle während der Umsetzung pflegen. Jeder übernommene Eintrag erhält darunter einen Detailblock gemäß Abschnitt 5.2. „Offen“ bedeutet ausdrücklich nicht implementiert oder nicht anhand der Abnahme nachgewiesen.

| Paket | Status | Verantwortlich | Letzter Checkpoint / nächster Schritt |
| --- | --- | --- | --- |
| EXEC-01 | abgeschlossen | Codex | Ausgangsstand, Plan, Agent-Regeln und Testbasis gesichert; 48 Backend- und 66 Frontendtests bestanden. |
| SEC-01 | in Arbeit | Codex | SEC-01.5 `4db95c8`; SEC-01.6: 76/76 relevante Backendtests bestanden; weitere Endpunkte offen. |
| SEC-02 | offen | — | Zielabteilungen und Relationsprüfungen inventarisieren. |
| SEC-03 | offen | — | Listenmigration und Zugriffstests vorbereiten. |
| SEC-04 | offen | — | HTML-Ein-/Ausgabepfade und gemeinsame Bereinigung erfassen. |
| SEC-05 | offen | — | Medieninventar und private Auslieferungsverträge erstellen. |
| SEC-06 | offen | — | Schlüssel- und Zugangsdatenmigration ausarbeiten. |
| SEC-07 | offen | — | Sitzungs-, MFA- und OIDC-Verträge implementierbar aufteilen. |
| SEC-08 | offen | — | Formelübernahme in dauerhaftem Exporttest reproduzieren. |
| SEC-09 | offen | — | Bestandsbuchungen und Änderungsrouten absichern. |
| SEC-10 | offen | — | Versions-/Abhängigkeitsprüfung und Produktionschecks. |
| ROLE-01 | offen | — | Rollenmanifest auf Django-Permissions abbilden. |
| ROLE-02 | offen | — | Delegationsregeln und Zuweisungsoberfläche. |
| CFG-01 | offen | — | Vollständigen Einstellungskatalog mit Quelle/Berechtigung erstellen. |
| TRAIN-01 | offen | — | Atomarer Planvertrag und Versionsprüfung. |
| TRAIN-02 | offen | — | Stationen, Rotation und Ressourcenwarnungen. |
| TRAIN-03 | offen | — | Verlustfreie Serien, Vorlagen und Dienstverknüpfung. |
| TRAIN-04 | offen | — | Mobile Durchführung, Handout und Nachbereitung. |
| DES-01 | offen | — | Designsystem und fünf Referenzansichten. |
| UX-01 | offen | — | Dashboard-Zusammenfassungen und Aufgaben. |
| UX-02 | offen | — | Mitglieder-/Eltern-/Gruppenabläufe. |
| UX-03 | offen | — | Listen- und Ereignisansichten. |
| UX-04 | offen | — | Dienstbuch und mobile Erfassung. |
| UX-05 | offen | — | Inventar-/Bestellabläufe nach SEC-09. |
| UX-06 | offen | — | Qualifikationen und Nachweise. |
| UX-07 | offen | — | E-Mail-Prüfung, Auftrag und Versandstatus. |
| UX-08 | offen | — | Sync-Vorschau und Profileinstellungen. |
| OPS-01 | offen | — | Gemeinsamen Installationskern und Adapter festlegen. |
| OPS-02 | offen | — | Assistent mit vollständiger Vorabprüfung. |
| OPS-03 | offen | — | Einheitliche Host-CLI mit Menü und Unterbefehlen. |
| OPS-04 | offen | — | Konsistente Backups, Restore und Releasewechsel. |
| OPS-05 | offen | — | Altvarianten und Migrationspfade konsolidieren. |
| DOC-01 | offen | — | Nach Funktionsabschluss vollständige bebilderte Dokumentation. |

### EXEC-01: aktueller Detailstand

- **Status:** abgeschlossen mit diesem Commit.
- **Verantwortlich:** Codex.
- **Abhängigkeiten:** keine; vorhandener Arbeitsstand muss geschützt werden.
- **Ziel:** Verbindlicher, während der Umsetzung gepflegter Plan mit einem gemeinsamen Branch und nachvollziehbaren Teilschritt-Commits.
- **Teilschritte:**
  - `EXEC-01.1`: Vollständigen Plan einschließlich Branch-/Commitregeln anlegen und prüfen. Erledigt in `3619a63`.
  - `EXEC-01.2`: Bestehenden Git-Arbeitsstand erfassen und sichern; Umsetzungsbranch anlegen/prüfen. Erledigt mit Ausgangs-Commit `b20e36f` vor diesem Planungs-Commit.
  - `EXEC-01.3`: Repository-`AGENTS.md` mit verbindlichem Plan-/Fortschrittsverweis ergänzen und separat committen. Erledigt in `7aeb4dd`.
  - `EXEC-01.4`: Testbasis prüfen und Ausgangsergebnisse dokumentieren; erste Regression folgt als `SEC-01.1`. Erledigt in `3669c4d`.
- **Letzter dauerhafter Checkpoint:** 03.10.2026, Agent-Regeln `7aeb4dd`; 48 Backend- und 66 Frontendtests bestanden.
- **Branch:** `feat/security-roles-training-operations`, von `main` bei `a04fc88`.
- **Geänderte Dateien:** `docs/planning/security-ux-design-roadmap.md`, `AGENTS.md`; vorbestehender Arbeitsstand separat in `b20e36f`.
- **Commit-Bezug:** Ausgangsstand `b20e36f`, Planungsdatei `3619a63`, Agent-Regeln `7aeb4dd`; dieser Commit: `test(EXEC-01.4): record baseline test results`.
- **Prüfungen:** Dokumentstruktur und `git diff --check` bestanden. Ausgewählte Backendtests (`departments.tests.test_department_scoping`, `api_tests.test_attachment_security`, `api_tests.test_user_security`): 48/48 bestanden. Gesamte Frontend-Unit-Suite: 66/66 bestanden. Erstversuche scheiterten an fehlenden Umgebungswerten und einem Intel-Node mit ARM-Rollup; mit Testschlüssel und ARM-Node erfolgreich wiederholt. Kein vollständiger Backend-Testlauf und keine Sicherheitsfreigabe.
- **Offene Risiken:** Ausgangsstand enthält frühere Änderungen aus mehreren Modulen; deren Qualität ist noch nicht erneut geprüft. Lokale `dump.rdb` bleibt unversioniert.
- **Laufende Prozesse:** keine durch diesen Planungsschritt.
- **Nächster Schritt:** `SEC-01.1`: dauerhafte Regression für abteilungsübergreifende Rechtevermischung.

### SEC-01: aktueller Detailstand

- **Status:** in Arbeit.
- **Verantwortlich:** Codex.
- **Abhängigkeiten:** EXEC-01 abgeschlossen; SEC-02 wird die Ziel- und Relationsprüfung aller Schreibaktionen ergänzen.
- **Ziel und Abnahme:** Aktionsrechte hängen von der tatsächlichen Objektabteilung ab. Ein Lesezugriff in B zusammen mit Schreibrecht in A erlaubt keine Änderung in B, unabhängig von Queryparametern. Vollqualifizierte Permissions und unbekannte Aktionen werden sicher behandelt.
- **Teilschritte:**
  - `SEC-01.1`: HTTP-Regression für gemischte Rollen A/B mit und ohne Abteilungsparameter, inklusive erlaubter Änderung in A.
  - `SEC-01.2`: Zentrale Modellrechte vollqualifiziert prüfen; Objektberechtigung für Datensätze mit `department_id` nach tatsächlicher Objektabteilung prüfen. Erledigt in `797d5d4`.
  - `SEC-01.3`: Staff- und Organisationsbereich ohne fachliche Rechte als HTTP-Regression testen. Rot nachgewiesen in `c6a55dc`.
  - `SEC-01.4`: Zentrale Rechte- und Listenfilter für Staff und organisationsweiten Bereich korrigieren. In diesem Commit erledigt.
  - `SEC-01.5`: Mitgliederlisten, Statistiken und Schreibzugriffe bei A/B-Rollen als Regression testen. In diesem Commit rot nachgewiesen.
  - `SEC-01.6`: Mitglieder nach tatsächlicher Abteilungsberechtigung filtern und gemeinsame Stammdaten objektbezogen schützen. In diesem Commit erledigt.
  - `SEC-01.7`: Weitere Objektbeziehungen, Listen und Sonderaktionen inventarisieren und gegen den vollständigen Vertrag testen.
- **Letzter dauerhafter Checkpoint:** SEC-01.5 `4db95c8`; SEC-01.6 nach 76 bestandenen Backendtests in diesem Commit.
- **Branch:** `feat/security-roles-training-operations`.
- **Geänderte Dateien / Commit-Bezug:** Regressionen `3f78cc8`, `c6a55dc`, `4db95c8`; Korrekturen `797d5d4`, `033f3bf`; `backend/jf_manager_backend/permissions.py`, `backend/members/api/viewsets/member_viewsets.py`, Member-Test und Journal in diesem Commit: `fix(SEC-01.6): scope member reads and writes to permitted departments`.
- **Umgesetzte Teilschritte:** `SEC-01.1`/`.3`/`.5` rot nachgewiesen; `SEC-01.2`/`.4`/`.6` korrigiert. Mitgliederdaten mit mehreren Abteilungen nutzen beim Lesen nur Abteilungen mit Leserecht; bei gemeinsam zugeordneten Mitgliedern genügt Schreibrecht in einer zugehörigen Abteilung für gemeinsame Stammdaten. Statistik zählt nur sichtbare Mitglieder und zeigt keine Gruppen aus fremden Datensätzen.
- **Ausgeführte Prüfungen mit Ergebnis:** Vor SEC-01.5: 263/263 Backendtests bestanden. Neue Member-Tests vor Fix: 1/4 bestanden, 3 rot. Nach Fix: 76/76 relevante Backendtests einschließlich Member-, Rollen- und Scoping-Tests bestanden. Vollständiger 263er-Lauf nach SEC-01.6 nicht erneut ausgeführt. Ruff und `git diff --check` bestanden; bestehende unsortierte lokale Imports im bearbeiteten ViewSet wurden formatiert. `manage.py test` ohne explizite Module scheitert an vorhandenem Namenskonflikt von `inventory/tests.py` und `inventory/tests/`.
- **Offene Fehler / Risiken:** Objektmodelle ohne einzelnes `department_id`, eigene ViewSet-Listenfilter, Sonderaktionen und weitere lokal codierte Staff-Bypässe sind offen. `SEC-01` ist noch nicht vollständig abgenommen.
- **Laufende Prozesse und sichere Fortsetzung:** keine; letzter breiter Testbericht `/tmp/jf-manager-backend-tests-final.log`.
- **Nächster konkreter Schritt:** `SEC-01.7` nach Risiko aufteilen, insbesondere Parent/Qualifikation, eigene Statistikaktionen und Staff-Bypässe.

## 7. Fortlaufendes Arbeitsjournal

Neue Einträge anhängen. Frühere Ergebnisse nicht nachträglich als erfolgreicher darstellen; Korrekturen als neuen Eintrag dokumentieren. Bei jeder Aktualisierung auch die Wiederaufnahmeübersicht und den betreffenden Paketstatus prüfen.

| Zeitpunkt | Paket / Teilschritt | Änderung / Erkenntnis | Prüfung / Ergebnis | Commit-Bezug | Nächster Schritt |
| --- | --- | --- | --- | --- | --- |
| 03.10.2026 | Audit vor Umsetzung | Sicherheits-, Design-, Rollen-, Übungsplanungs- und Betriebsanalyse abgeschlossen; Entscheidungen mit dem Nutzer festgelegt. | 51 ausgewählte Backendtests und 26 Frontendtests bestanden; fünf zusätzliche Auditbefunde isoliert reproduziert. Keine vollständige Produktabnahme. | Temporäre Auditprüfungen; kein Roadmap-Implementierungscommit. | Auditbefunde in dauerhafte Regressionstests überführen. |
| 03.10.2026 | EXEC-01.1 | Vollständige Planungsdatei angelegt. Ein gemeinsamer Feature-Branch, ein eigener Commit pro Teilschritt und laufende Checkpoints verbindlich ergänzt. | Strukturprüfung bestanden: 33 eindeutige Pakete, erforderliche Arbeitsregeln, ausgeglichene Codeblöcke und keine nachgestellten Leerzeichen. `git diff --check` ohne Befund; Anwendungscode unverändert. | Noch nicht committed; Planungs-Commit beim Start des Umsetzungsbranches vorgesehen. | Ausgangsstand schützen, Branch anlegen/prüfen und Planungsdatei separat committen. |
| 03.10.2026 | EXEC-01.2 | 102 vorbestehende Dateien geprüft, als Ausgangsstand auf neuem Branch gesichert. Redis-Datendatei `dump.rdb` ausgeschlossen. | Staged-Diff ohne Whitespacefehler; Anwendungstests für diesen Sicherungsschritt nicht ausgeführt. | `b20e36f` | Planungsdatei separat committen. |
| 03.10.2026 | EXEC-01.1 | Planungsdatei nach Sicherung des Ausgangsstands aktualisiert. | `git diff --check` vor Commit erneut prüfen; keine Anwendungstests für Markdown. | Dieser Commit: `docs(EXEC-01.1): record security and product roadmap` | `EXEC-01.3`: Repository-`AGENTS.md`. |
| 03.10.2026 | EXEC-01.3 | `AGENTS.md` als Einstiegspunkt mit Branch-, Teilschritt- und Journalregeln ergänzt. | Dokumentprüfung und `git diff --check` vor Commit; Anwendungstests für reine Anweisung nicht ausgeführt. | Dieser Commit: `docs(EXEC-01.3): add roadmap instructions for agents` | Testbasis prüfen. |
| 03.10.2026 | EXEC-01.4 | Lokale Backend- und Frontend-Testumgebung gefunden; wiederholbare Ausgangsprüfung durchgeführt. | 48/48 ausgewählte Backendtests und 66/66 Frontend-Unit-Tests bestanden. Kein Gesamttest. | Dieser Commit: `test(EXEC-01.4): record baseline test results` | SEC-01.1 übernehmen und Regression schreiben. |
| 03.10.2026 | SEC-01.1 | HTTP-Test für Schreibrecht in A, Leserecht in B und PATCH auf Gruppen in beiden Abteilungen. | 2/3 bestanden; fremder PATCH ohne Queryparameter antwortet 200 statt 403. Erwarteter roter Sicherheitsbefund; Test bleibt bis zur Korrektur fehlgeschlagen. | Dieser Commit: `test(SEC-01.1): expose cross-department write leakage` | SEC-01.2 Rechteprüfung nach Objektabteilung. |
| 03.10.2026 | SEC-01.2 | Zentrale Rollenprüfung nutzt App-Label und Codename; bei Datensätzen mit `department_id` wird die tatsächliche Objektabteilung geprüft. | 51/51 ausgewählte Backendtests bestanden; zusätzlicher Codename-Test ergibt 4/4 Regressionstests. Andere Objektbeziehungen und Sonderaktionen noch nicht abgenommen. | Dieser Commit: `fix(SEC-01.2): enforce department-scoped object permissions` | SEC-01.3 weitere Zugriffspfade und Staff-Bypässe. |
| 03.10.2026 | SEC-01.3 | HTTP-Tests für Staff ohne Fachrecht, organisationsweiten Bereich ohne Fachrecht und Staff mit Rolle nur in A. | 1/4 bestanden, 3 erwartungsgemäß fehlgeschlagen: unberechtigtes Lesen und fremde Datensätze in Listen. | Dieser Commit: `test(SEC-01.3): expose staff and scope permission bypasses` | SEC-01.4 Rechte- und Listenfilter korrigieren. |
| 03.10.2026 | SEC-01.4 | Staff-Bypass entfernt, Bereich und Modellrechte getrennt, Leselisten mit Abteilungsrollen gefiltert; veraltete Sync- und Scoping-Testvorbereitungen auf explizite Rechte umgestellt. | 263/263 Backendtests über explizite Module, 10/10 Sicherheitsregressionen, Ruff und Diff-Check bestanden. Vorheriger breiter Lauf: 9 veraltete Sync-Fixture-Annahmen; korrigiert. Discovery ohne Modulliste weiterhin defekt. | Dieser Commit: `fix(SEC-01.4): separate scope from model permissions` | SEC-01.5 weitere Objektbeziehungen, Sonderaktionen und lokale Bypässe. |
| 03.10.2026 | SEC-01.5 | Vier HTTP-Regressionen für Mitglieder mit Abteilungen A, B und A/B ergänzt. | 1/4 bestanden; Liste und Statistik enthalten fremdes B-Mitglied, PATCH auf B wird trotz Schreibrecht nur in A mit 200 akzeptiert. | Dieser Commit: `test(SEC-01.5): expose member scope and statistics leakage` | SEC-01.6 Queryset und Objektprüfung. |
| 03.10.2026 | SEC-01.6 | Member-Queryset nach Modellrecht gefiltert, Statistik auf sichtbare Mitglieder begrenzt, Objektprüfung für M2M-Abteilungen ergänzt. | 76/76 relevante Backendtests bestanden; zusätzliche Gruppenname-Prüfung grün. Gesamte 263er-Suite nach dieser Änderung nicht erneut ausgeführt. | Dieser Commit: `fix(SEC-01.6): scope member reads and writes to permitted departments` | SEC-01.7 weitere Zugriffspfade priorisieren. |
