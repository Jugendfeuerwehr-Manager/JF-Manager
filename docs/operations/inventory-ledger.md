# Bestandsbuchungen

Bestände ändern sich ausschließlich durch Buchungen: Eingang, Ausgabe/Ausleihe, Rückgabe, Umlagerung und Aussortierung. Gebuchte Bewegungen sind unveränderlich. Fehler werden durch eine Gegenbuchung („Stornieren“) korrigiert.

## Schutzmechanismen

- Anwendung: Buchungen lassen sich weder ändern noch löschen, auch nicht per Massenänderung oder Kaskade. Bestände mit Menge lassen sich nicht direkt setzen oder löschen.
- PostgreSQL: Ein Trigger (`inventory.0016`) verbietet `UPDATE` und `DELETE` auf gebuchten Bewegungen. Ausnahme ist das Leeren ehemaliger Mitgliedsnamen (Datenschutz). Das gilt auch für direkte SQL-Zugriffe. `TRUNCATE` ist nicht abgefangen.
- Anfangsbestände und Beispieldaten werden als Eingangsbuchung erfasst (`inventory.opening_stock.book_opening_stock`). `create_inventory_sample_data --clear` verweigert, sobald Buchungen existieren.

Datenkorrekturen außerhalb von Gegenbuchungen sind nur nach Backup, im Wartungsfenster und mit ausdrücklich deaktiviertem Trigger zulässig. Den Eingriff dokumentieren.

## Doppelbuchungen bei Wiederholung

Die Oberfläche sendet bei Buchungen, Sammelausgaben und Wareneingängen von Bestellpositionen einen `Idempotency-Key`. Wiederholt jemand dieselbe Aktion nach einem Verbindungsabbruch, Timeout oder Doppelklick, liefert der Server das gespeicherte Ergebnis statt einer zweiten Buchung. Eine andere Anfrage mit derselben Kennung wird mit 409 abgewiesen.

Gespeicherte Antworten enthalten Buchungsdetails. `python manage.py purge_booking_requests` täglich ausführen. Die Aufbewahrung steuert `BOOKING_REPLAY_RETENTION_DAYS` (Standard 30 Tage). Danach ist eine Wiederholung mit alter Kennung eine neue Buchung.

## Prüfung auf PostgreSQL

SQLite serialisiert Schreibzugriffe und zeigt weder verlorene Änderungen noch Deadlocks. Konkurrenz- und Triggerprüfungen (`inventory.tests.test_postgres_concurrency`, `inventory.tests.test_ledger_guards`) laufen deshalb nur gegen PostgreSQL und werden sonst übersprungen. Beispiel mit einer lokalen, leeren Testinstanz:

```sh
cd backend
DJANGO_SETTINGS_MODULE=jf_manager_backend.docker_settings \
DATABASE_URL=postgres://<user>@127.0.0.1:<port>/postgres \
STATIC_ROOT=/tmp/jf-static MEDIA_ROOT=/tmp/jf-media DEBUG=True REDIS_URL=none \
DJANGO_SECRET_KEY=<test> FIELD_ENCRYPTION_KEY=<fernet-test-key> \
python manage.py test inventory.tests --noinput
```

Sammelausgaben sperren alle betroffenen Bestandszeilen vorab in fester Reihenfolge. Parallele Ausgaben mit unterschiedlicher Positionsreihenfolge führen so nicht zu Deadlocks.
