# Handbuch pflegen und ausliefern

## Lokal bauen

Im Repository-Wurzelverzeichnis, mit Python 3.10 oder neuer:

```sh
python3 -m venv .venv-docs
.venv-docs/bin/python -m pip install -r requirements-docs.txt
.venv-docs/bin/python scripts/docs/build.py
```

Das Skript erzeugt `.docs-build/site/` und `.docs-build/jf-manager-handbook.zip`. Es baut mit MkDocs im strikten Modus und prüft danach sämtliche lokalen HTML-Links, Anker und Laufzeitassets. Ein fehlendes Bild, ein kaputter Link oder ein externer Laufzeitasset lässt den Build scheitern.

Die Quellen bleiben in `docs/handbook/` und den ausgewählten Betriebs-/Fachreferenzen. Der Build kopiert diese in einen temporären Quellenordner. Links zu technischen Dateien außerhalb des Handbuchs führen zum beim Build aktuellen Git-Commit. Solche weiterführenden Repository-Links brauchen Internetzugang. Roadmap, Marketingentwürfe, Anwendungsdateien, lokale Demo-Zugangsdaten und echte Daten gehören nicht ins Auslieferungspaket.

## Vorschau und eigenes Hosting

```sh
.venv-docs/bin/python -m http.server 8088 --bind 127.0.0.1 --directory .docs-build/site
```

Öffne `http://127.0.0.1:8088/`. Die Website besteht aus statischen HTML-, CSS-, JavaScript- und Bilddateien. Sie braucht weder Django noch Node auf dem Zielserver. Sie lässt sich auch unter einem Unterpfad wie `/handbuch/` hosten. Vor Auslieferung Build erneut ausführen; eine Änderung an Markdown allein ändert die fertige Website nicht.

Das ZIP vollständig entpacken und den Inhalt auf einen statischen Webserver kopieren. `index.html` ist der Einstieg. Die Navigation verwendet relative HTML-Pfade. Direktes Öffnen per `file://` ist zum Lesen möglich; **Suche funktioniert zuverlässig über HTTP**, weil der Browser den Suchindex laden muss. Für einzelne Artikel kann die Browser-Druckfunktion auch PDF erzeugen. Das ZIP ist kein einziges zusammenhängendes PDF-Handbuch.

Das [MkDocs-Auslieferungsverfahren](https://www.mkdocs.org/user-guide/deploying-your-docs/) beschreibt statisches Hosting. Schrift, Navigation, Suche und Styles des Builds verwenden lokale Assets; keine Analyse-/Trackingdienste werden eingebunden.

## GitHub Pages vorbereiten

Der Workflow **Benutzerhandbuch** baut und prüft bei Dokumentations-PRs sowie Änderungen auf `main` und stellt das Website-ZIP als herunterladbares Artefakt bereit. Diese Läufe veröffentlichen nichts.

Für eine Veröffentlichung durch die Projektverantwortlichen:

1. Den geprüften Stand nach `main` integrieren.
2. Im Repository unter **Settings → Pages → Build and deployment → Source** **GitHub Actions** wählen.
3. Die Umgebung `github-pages` auf den erlaubten Veröffentlichungsbranch `main` beschränken; gegebenenfalls Reviewregeln einrichten.
4. Unter **Actions → Benutzerhandbuch → Run workflow** Branch `main` und **Auf GitHub Pages veröffentlichen** aktivieren.
5. Nach erfolgreichem Deployment die ausgegebene URL öffnen und Navigation, Bilder und Suche prüfen.

Die getrennten Build-/Deployjobs folgen der [GitHub-Pages-Dokumentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages). Für den Deployjob sind `pages: write` und `id-token: write` vorgesehen. Die Repository-Einstellungen und eine tatsächliche Veröffentlichung sind gesonderte Betreiberaktionen; sie wurden bei Erstellung dieses Handbuchs nicht geändert.

## Aktuelle Screenshots erzeugen

Alle Bilder in `handbook/images/` stammen aus `backend/demo.py` und dem aktuellen `seed_demo`. Es werden keine bestehenden Datenbanken verwendet. `provenance.json` hält Aufnahmestand, Quelle und Größen fest. Der Abschnitt „App & Mitteilungen“ wird als gezielter Bildausschnitt aufgenommen. Das Konto ist ein Demo-Superuser; Fachkonten sehen entsprechend weniger Aktionen. Die produktive Push-Zustellung und echte Passkey-Geräte sind durch diese Aufnahmen nicht geprüft.

1. In `backend/` `PIPENV_DONT_LOAD_ENV=1 pipenv run python demo.py --port 8012` starten. Das Terminal nennt einen neuen temporären Ordner `jf-manager-demo-…`. Die Demo sperrt echten E-Mail-/Push-Versand.
2. In `frontend/` `VITE_BACKEND_URL=http://127.0.0.1:8012 npm run dev -- --host 127.0.0.1 --port 5174` starten. Andere laufende Dienste nicht ersetzen.
3. Außerhalb der Projektabhängigkeiten eine temporäre Aufnahmeumgebung einrichten:

```sh
mkdir -p /tmp/jf-handbook-capture
npm install --prefix /tmp/jf-handbook-capture --no-save playwright@1.56.1
/tmp/jf-handbook-capture/node_modules/.bin/playwright install chromium
```

4. Im Repository-Wurzelverzeichnis ausführen. Den tatsächlichen Demoordner einsetzen; der Pythonpfad wird aus der Backend-Pipenv-Umgebung ermittelt:

```sh
export JF_SCREENSHOT_DEMO_DIR=/PFAD/ZUM/jf-manager-demo-ORDNER
export JF_DEMO_PYTHON=$(cd backend && PIPENV_DONT_LOAD_ENV=1 pipenv --py)
export PLAYWRIGHT_MODULE=/tmp/jf-handbook-capture/node_modules/playwright
node scripts/docs/capture-screenshots.cjs
```

Alternativ kann `CHROME_PATH` auf ein installiertes Chrome zeigen. Zugangsdaten werden ausschließlich aus der geschützten temporären Demodatei gelesen. Der aktuelle TOTP-Code kommt aus `demo_totp`; das Skript fotografiert weder Passwort noch MFA-Code. Kein Produktionsziel verwenden.

5. Alle Bilder visuell auf Inhalt, Ladefehler und sichtbare Geheimnisse prüfen, Text und Bildunterschriften abgleichen, anschließend Handbuch neu bauen. `captured_on` im Aufnahme-Skript auf den tatsächlichen Tag setzen. Änderungen samt Herkunftsdatei committen.
6. Eigene Demo-/Vite-Prozesse nach der Aufnahme beenden. Temporäre Daten nicht als Projektartefakte ausliefern.

## Redaktionelle Pflege

Bei Änderungen eines Fachablaufs die zugehörige Rollenseite, Bilder und README gemeinsam prüfen. Bildschirmabbildungen erklären eine Aufgabe und erhalten Alternativtext sowie Bildunterschrift. Noch nicht abgenommene Funktionen ausdrücklich als Entwicklung kennzeichnen. Nach Fachabnahme des Portals eigene Portalabläufe ergänzen.
