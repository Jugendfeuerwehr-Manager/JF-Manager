# Sicherheitsupdate: Installation und Betrieb

Dieses Update schließt konkrete Übernahme- und Rechteausweitungswege. Es ersetzt keine vollständige Sicherheitsprüfung des gesamten Produkts.

## Vor dem Update

1. Datenbank und Medien sichern. Einen funktionierenden lokalen Superuser-Zugang bereithalten.
2. Für bestehende OIDC-Konten beim Identitätsanbieter **Issuer (`iss`) und unveränderliches Subject (`sub`)** ermitteln und die Zuordnung zum richtigen Benutzer unabhängig überprüfen. E-Mail-Adressen reichen dafür nicht aus.
3. Wartungsfenster ankündigen: bestehende JWT-Anmeldungen werden durch die neue Passwortbindung ungültig. Nutzer melden sich einmal neu an.

## Update ausrollen

Backend und Frontend gemeinsam aktualisieren, dann im Backend ausführen:

```sh
python manage.py migrate
```

Das installiert die SimpleJWT-Blacklist und die OIDC-Identitätsfelder. Ohne Migration darf die neue Version nicht produktiv gestartet werden.

Bestehende OIDC-Konten werden **nicht automatisch über E-Mail übernommen**. Nach unabhängig geprüfter Zuordnung jedes bisherige OIDC-Konto einmal explizit binden:

```sh
python manage.py bind_oidc_identity BENUTZERNAME https://idp.example.org UNVERAENDERLICHES_SUBJECT
```

Der Befehl akzeptiert ausschließlich vorhandene OIDC-Konten und überschreibt keine bestehende Bindung. Neue OIDC-Konten werden beim ersten Login gebunden; hierfür muss der Anbieter `email_verified: true` liefern. Bei einem Anbieterwechsel muss die Identitätsmigration geplant werden. Lokale und LDAP-Konten werden nicht automatisch in OIDC-Konten umgewandelt.

In der regulären Wartung abgelaufene Token-Einträge entfernen:

```sh
python manage.py flushexpiredtokens
```

## Geänderte Schutzmaßnahmen

- `/users/` erstellt keine Konten mehr. Profile dürfen nur durch ihren Eigentümer geändert werden; Rechte- und Aktivierungsfelder sind dort schreibgeschützt. Fremde Detailansichten enthalten nur die bereits im Benutzerverzeichnis sichtbaren Basisdaten.
- Benutzer-, Gruppen- und Abteilungsrollenverwaltung: **nur Superuser schreiben**, Staff liest. Das verhindert, dass ein Staff-Konto sich selbst oder anderen höhere Rechte zuweist oder Administratorpasswörter ersetzt.
- Anhänge übernehmen Sichtbarkeit und Änderungsrechte ihres zugehörigen Mitglieds, ihrer Liste oder ihres Ausbildungsbausteins. Der generische Upload-Endpunkt ist geschlossen; Mitglieder-Uploads verwenden `/members/{id}/attachments/` mit serverseitig aufgelöster Zuordnung. Elternverwaltung verlangt Modellberechtigungen und lässt keine Verknüpfung mit fremden Mitgliedern zu.
- Reset-Links gelten eine Stunde, werden nach Passwort- oder E-Mail-Änderung ungültig und können nicht für deaktivierte Konten verwendet werden. Doppelte E-Mail-Adressen führen zu einer generischen Antwort ohne Reset.
- Passwortänderungen widerrufen JWT-Zugang, JWT-Refresh und klassische API-Token. Django-Sitzungen prüfen den geänderten Passwort-Hash bei der nächsten Anfrage.
- Refresh-Tokens rotieren und verwendete Tokens stehen auf der Blacklist. Das Frontend speichert den neuen Refresh-Token und bündelt parallele Erneuerungen. Ein später Refresh darf einen bereits erfolgten Logout nicht rückgängig machen.
- Lokaler Login und klassische Token-Anmeldung begrenzen anonyme Versuche auf zehn pro Minute je IP; Passwortaktionen auf fünf pro Minute je IP.
- OIDC-Konten sind dauerhaft an Issuer und Subject gebunden, mit Datenbank-Eindeutigkeit. Eine inzwischen neu vergebene E-Mail-Adresse oder ein gleichlautender Benutzername kann kein gebundenes Konto übernehmen. Extern verwaltete E-Mail-Adressen sind im eigenen Profil nicht änderbar.

## Nach dem Update prüfen

Mit normalem Benutzer, Staff und Superuser die zulässigen Aufgaben testen. Insbesondere fremde Profiländerungen und Staff-Schreibzugriffe müssen scheitern. Einen Reset durchführen und prüfen, dass derselbe Link und vorherige Anmeldetokens anschließend abgewiesen werden. OIDC mit einem bestehenden, explizit gebundenen Konto testen.

Automatisierte Regressionstests:

```sh
cd backend
PIPENV_DONT_LOAD_ENV=1 DJANGO_SECRET_KEY=local-test-only-secret-key-32-chars REDIS_URL=none pipenv run python manage.py test api_tests.test_user_security api_tests.test_admin_users api_tests.test_attachment_security users.tests
cd ../frontend
npm run test:unit -- --run src/api/__tests__/token-refresh.spec.ts
```

Die Tests behandeln Profilübernahme, Staff-Eskalation, einmalige Reset-Links, Token-Widerruf, Refresh-Replay, Loginbegrenzung, OIDC-Übernahmeversuche und sichere explizite Altbestandsbindung. Frontendtests prüfen parallele Refresh-Anfragen, Rotation und Logout während einer Erneuerung.

## Betriebsgrenzen

Drosselung benutzt den konfigurierten Django-Cache. Mehrere Backend-Prozesse benötigen einen gemeinsamen Cache, etwa Redis, damit das Limit gemeinsam zählt. Reverse Proxy und vertrauenswürdige Proxy-Adressen korrekt konfigurieren; ergänzende Limits am Proxy schützen auch vor verteilten Angriffen. Die Anwendung verwendet weiterhin Browser-Speicher für JWTs; Schutz vor eingeschleustem JavaScript bleibt daher wichtig. Ein privilegierter Identitätsanbieter und Superuser bleiben Vertrauensinstanzen. Der Benutzerverzeichnis-Endpunkt bleibt für angemeldete Benutzer sichtbar. Diese Änderungen sind gezielte Regressionen, kein vollständiger Penetrationstest oder Zusicherung, dass sämtliche weiteren API-Routen sicher sind.


### Noch offen: direkter Zugriff auf hochgeladene Dateien

Die Standard-Anhangpfade unter `/uploads/attachments/` werden im mitgelieferten Nginx und im Django-Entwicklungsserver gesperrt. Die API gibt für berechtigt sichtbare Anhänge fünf Minuten gültige, signierte Vorschau-Links aus; Downloads über `/attachments/{id}/download/` prüfen weiterhin die Anmeldung und die Rechte des Besitzers. Eigene Reverse-Proxy-Konfigurationen müssen denselben direkten Pfad sperren; bei verändertem `ATTACHMENT_UPLOAD_FOLDER` ist die Sperre entsprechend anzupassen. Vorschau-Links sind während ihrer kurzen Gültigkeit an jeden mit dem Link weitergebbar.

Andere Medienpfade (etwa Avatare, Trainingsmedien und E-Mail-Anhänge) werden weiterhin direkt aus `/uploads/` ausgeliefert. Für vertrauliche Daten in diesen Pfaden ist vor dem Produktiveinsatz eine getrennte Zugriffslösung nötig. Diese Änderungen sind kein vollständiger Schutz aller hochgeladenen Dateien.

Für einen vollständig geschützten Medienbetrieb müssen private Uploads über authentifizierte, objektbezogen autorisierte Downloads oder kurzlebige Download-Freigaben ausgeliefert werden. Der direkte öffentliche Pfad und öffentliche Cache-Einträge müssen dabei entfallen. Vorschauen, Mitgliederbilder und Ausbildungsmedien verwenden derzeit direkte URLs und müssen im selben Schritt angepasst werden; ein pauschales Sperren des Verzeichnisses würde diese Funktionen unterbrechen. Dies ist ein verbleibender Befund, keine durch dieses Update bereits erledigte Absicherung. `DEBUG` darf in Produktion nicht aktiviert sein.
