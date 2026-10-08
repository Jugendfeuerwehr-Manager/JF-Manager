# Web-App und Push einrichten

JF-Manager ist als Web-App auf dem Startbildschirm installierbar. Der Service Worker hält ausschließlich eine öffentliche Offline-Hinweisseite vor. Mitgliederdaten, Anhänge und API-Antworten werden nicht für den Offlinebetrieb zwischengespeichert. Anwesenheiten lassen sich nur mit einer Verbindung speichern.

## Voraussetzungen

- Eine öffentliche **HTTPS-Adresse** und korrekt eingerichteter Reverse Proxy. `localhost` dient nur zur Entwicklung.
- Aktuelle Datenbankmigrationen (`python manage.py migrate`).
- Backend-Abhängigkeiten aus `backend/Pipfile.lock`, einschließlich `pywebpush`.
- Für Push: ein dauerhaftes VAPID-Schlüsselpaar und ein laufender Versandprozess.

Das Verfahren verwendet die standardisierte [Push API](https://developer.mozilla.org/en-US/docs/Web/API/PushManager/subscribe) und [pywebpush](https://github.com/web-push-libs/pywebpush).

## Schlüssel und Konfiguration

Einmal auf einem vertrauenswürdigen Rechner erzeugen:

```sh
cd backend
pipenv run python manage.py generate_push_keys
```

Die beiden ausgegebenen Werte in der serverseitigen `.env` speichern:

```dotenv
WEB_PUSH_PUBLIC_KEY=<ausgegebener öffentlicher Schlüssel>
WEB_PUSH_PRIVATE_KEY=<ausgegebener privater Schlüssel>
WEB_PUSH_SUBJECT=mailto:administration@eure-domain.de
FRONTEND_URL=https://jf.eure-domain.de
```

Private Schlüssel niemals in Git oder Frontend-Variablen ablegen. Schlüssel bei Updates beibehalten; nach einer Rotation müssen Nutzer die Geräte-Abonnements neu aktivieren. Ohne vollständige Konfiguration zeigt das Profil einen Hinweis statt eines wirkungslosen Aktivierungsknopfs.

## Versand starten

Beide Produktionswege starten den Versand automatisch: Docker Compose mit dem Dienst `push-worker`, Debian 13 nativ mit `jf-manager-push.service` (siehe [Betrieb](operations/ops-overview.md)). Der Worker bearbeitet die Warteschlange alle 15 Sekunden und nutzt dasselbe Backend, dieselbe Datenbank und dieselben VAPID-Schlüssel. Lokal (Entwicklung) läuft er so:

```sh
python manage.py send_push --loop
```

Alternativ einmalig ausführen, etwa über einen vorhandenen Zeitplan:

```sh
python manage.py send_push
```

Ereignisse werden zuerst in der Datenbank vorgemerkt; die API-Anfrage wartet nicht auf den Push-Anbieter. Temporäre Fehler werden begrenzt erneut versucht. Abgelaufene Abonnements werden bei HTTP 404/410 entfernt, Meldungen nach einem Tag verworfen. Das ist eine Best-Effort-Benachrichtigung, keine Alarmierung mit Zustellgarantie. Bei Ausfällen kann ein Worker eine Meldung erneut zustellen; die Benachrichtigungskennung fasst gleichartige Hinweise auf dem Gerät zusammen.

## Was löst eine Nachricht aus?

| Auswahl im Profil | Ereignisse |
| --- | --- |
| Dienste | Dienst neu angelegt; Änderungen an Zeit, Ort, Thema, Beschreibung, besonderen Vorkommnissen oder Abteilung |
| Bestellungen | Neue Bestellung; dokumentierter Statuswechsel eines Bestellartikels |
| Test senden | Testnachricht ausschließlich an das aktuelle, registrierte Gerät |

Anwesenheitsklicks lösen keine Push-Flut aus. Direkte Datenbankänderungen oder Bulk-Updates, die Django-Signale umgehen, erzeugen keine Meldungen. Empfänger benötigen aktuelle Leserechte auf das jeweilige Objekt; die Rechte werden sowohl beim Vormerken als auch vor dem Versand geprüft. Der Sperrbildschirm enthält allgemeine Hinweise und keine Mitgliedernamen. Öffnen führt zum entsprechenden Modul, dessen API weiterhin eine Anmeldung verlangt.

## Einrichtung durch Nutzer

1. Im Browser installieren: Android/Desktop über das Browser-Menü; iPhone/iPad über Safari → Teilen → **Zum Home-Bildschirm**.
2. Auf iPhone/iPad die installierte App öffnen (Web Push ab iOS/iPadOS 16.4); Unterstützung hängt von Browser und Gerät ab.
3. **Mein Profil → App & Mitteilungen** öffnen.
4. Dienste und/oder Bestellungen auswählen, **Mitteilungen aktivieren** wählen und die Browserabfrage bestätigen.
5. **Test senden** wählen. Trifft nichts ein, Worker, HTTPS, VAPID-Konfiguration und Browser-/Betriebssystemberechtigungen prüfen.
6. **Ausschalten** beendet das Abonnement dieses Geräts. Abmelden meldet das Browser-Abonnement ebenfalls ab; nach erneutem Login bewusst wieder aktivieren.

Abonnements gelten pro Konto und Browsergerät; maximal zehn Geräte pro Konto. Bei geteilten Geräten stets abmelden. Browserberechtigungen lassen sich nach einer Ablehnung in den Website-Einstellungen ändern. Push-Dienste erhalten die für die Zustellung nötigen Metadaten; die Nutzlast wird durch Web Push verschlüsselt.

## Update und Kontrolle

`/sw.js` und `/manifest.webmanifest` dürfen nicht langfristig unveränderlich gecacht werden. Die mitgelieferte Nginx-Konfiguration berücksichtigt dies; eigene Reverse Proxys entsprechend konfigurieren.

```sh
PIPENV_DONT_LOAD_ENV=1 DJANGO_SECRET_KEY=local-test-only-secret-key-32-chars REDIS_URL=none pipenv run python manage.py test notifications
```

Diese Tests simulieren den Push-Anbieter und prüfen Berechtigungen, Gerätezuordnung, unerlaubte Ziele, Ereignisverarbeitung und Wiederholungen. Eine echte Zustellung benötigt eingerichtete Produktionsschlüssel, einen freigegebenen Browser und einen laufenden Worker.
