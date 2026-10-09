# Regelbetrieb, Sicherung und Updates

## Regelmäßig kontrollieren

```sh
sudo jfctl status
sudo jfctl doctor
sudo jfctl workers status
sudo jfctl maintenance list
sudo jfctl backup list
sudo jfctl backup verify latest
```

Prüfe letzte erfolgreiche Sicherung, Speicherplatz, Erreichbarkeit, Timer und Worker. `backup verify` liest den gewählten Snapshot und kontrolliert Dump, Uploads und Schlüssel; es ersetzt keine praktische Wiederherstellungsprobe. Plane diese mindestens vierteljährlich auf einem getrennten Testsystem ein.

## Sicherung und Wiederherstellung

Eine Sicherung hält Anwendung und Worker kurz an und enthält Datenbank, Uploads, Konfiguration, Schlüssel und Manifest. Das Backup-Passwort gehört zusätzlich außerhalb des Servers in einen geeigneten sicheren Speicher. Verwende ein Sicherungsziel auf einem anderen Gerät.

Vor Restore Snapshot-ID, Zielinstanz und Version prüfen. Der Vorgang ersetzt Daten und verlangt ausdrücklich den Instanznamen. Danach werden Sitzungen verworfen und Worker bleiben angehalten. Prüfe Anmeldung, Datenbestand, Anhänge, E-Mail- und Synchronisationsaufträge, bevor du `sudo jfctl workers release` ausführst. Das verhindert ungeprüften Versand aus alten Warteschlangen.

Die vollständige Schrittfolge steht unter [Backup und Restore](../../operations/ops-backup-restore-update.md).

## Ein Update vorbereiten

1. Änderungen des Zielreleases und verfügbare Artefakte prüfen; Wartungszeit ankündigen.
2. `status`, `doctor` und Sicherungsverifikation ausführen. Auch den extern gesicherten Backup-Zugang prüfen.
3. `sudo jfctl update --version X.Y.Z` mit der tatsächlich gewählten Version ausführen. `X.Y.Z` ist ein Platzhalter.
4. Rückgabecode und Status beachten. Anmeldung und zentrale Fachabläufe nach Freigabe kontrollieren.

`jfctl` prüft das Release, erstellt eine vollständige Sicherung und führt Migrationen aus. Bei Fehlern vor Freigabe erfolgt der dokumentierte automatische Rückfall. Nach Freigabe und neuen Schreibzugriffen ist ein bloßer Imagewechsel keine geeignete Rückkehr; eine gezielte Wiederherstellung kann neue Daten verlieren und muss abgestimmt werden.

## Wartung und Protokolle

Systemd-Timer übernehmen Sitzungsbereinigung, Audit-/Buchungsbereinigung, fällige Synchronisation und Sicherung. Bestellerinnerungen sind zunächst ausgeschaltet, weil sie Nachrichten versenden. Die [CLI-Referenz](../../operations/ops-jfctl.md#wartungsplan) beschreibt den Plan.

```sh
sudo jfctl logs jfctl
sudo jfctl logs -n 100
```

Für einen konkreten Dienst den Namen des Betriebswegs wählen: Compose `backend`, `worker`, `push-worker`, `frontend`; nativ `web`, `worker`, `push`, `nginx`. Protokolle intern prüfen und vor Weitergabe auf sensible Inhalte kontrollieren.
