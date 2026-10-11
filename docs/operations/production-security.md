# Produktionsvorgaben: HTTPS, Proxy und Sicherheitsheader

Gilt ab SEC-10.3. Ergänzt [session-auth.md](session-auth.md).

## HTTPS ist Pflicht

Ohne `DEBUG` sind Cookies `Secure`, das Backend leitet HTTP auf HTTPS um und sendet HSTS für ein Jahr. Ausgenommen ist nur `/health/`, damit der Container-Healthcheck intern über HTTP prüfen kann.

| Variable | Wirkung | Standard |
| --- | --- | --- |
| `SECURE_SSL_REDIRECT` | HTTPS-Umleitung im Backend | wie `SECURE_COOKIES` |
| `SECURE_HSTS_SECONDS` | HSTS-Dauer; `0` schaltet ab | `31536000` |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | HSTS auch für Subdomains | `false` |
| `SECURE_HSTS_PRELOAD` | Preload-Kennzeichen | `false` |
| `TRUST_PROXY_SSL_HEADER` | `X-Forwarded-Proto: https` als Nachweis akzeptieren | `true` |

HSTS lässt sich im Browser nicht zurücknehmen, bevor die Dauer abläuft. Vor dem ersten Produktivstart prüfen, dass die Adresse dauerhaft per HTTPS erreichbar ist. Subdomains und Preload nur aktivieren, wenn alle Subdomains der Organisation HTTPS sprechen.

## Reverse Proxy

TLS endet am vorgeschalteten Proxy (z. B. Traefik, Caddy, Nginx). Dieser muss

- `X-Forwarded-Proto` **selbst setzen und einen vom Client mitgeschickten Wert überschreiben**,
- der einzige Weg zum Frontend-Container sein (Port 8080 nicht öffentlich freigeben).

Der mitgelieferte Nginx im Frontend-Container reicht `X-Forwarded-Proto` an das Backend weiter. Wird er ohne vorgeschalteten Proxy direkt aus dem Netz erreicht, könnte ein Client HTTPS vortäuschen. In diesem Fall `TRUST_PROXY_SSL_HEADER=false` setzen und TLS direkt im Nginx terminieren.

## Prüfung

```sh
cd backend
DJANGO_SETTINGS_MODULE=jf_manager_backend.docker_settings python manage.py check --deploy
```

Erwartet: keine `security.*`-Meldung. Die Meldung `orders.OrderableItem.inventory_item (fields.W342)` ist vorbestehend und sicherheitsneutral. Die Hinweise zu HSTS-Subdomains und -Preload (`security.W005`, `security.W021`) sind bewusst stummgeschaltet (siehe oben). Der automatische Test `api_tests.test_production_settings` prüft dieselben Vorgaben.

## Sicherheitsheader und Content-Security-Policy

Gilt ab SEC-13: Die Content-Security-Policy (CSP) wird **durchgesetzt**.

Der Nginx im Frontend-Container setzt für alles, was er selbst ausliefert (Oberfläche, Assets, `/static/`, Service Worker, Manifest), über `/etc/nginx/snippets/security-headers.conf` (Quelle: `frontend/snippets/`): `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin`, `Cross-Origin-Opener-Policy: same-origin`, `Permissions-Policy` und die CSP. Antworten des Backends (`/api/`, `/admin/`, API-Dokumentation) erhalten dieselbe CSP und `Permissions-Policy` von Django (`jf_manager_backend.csp`); Nginx fügt dort keine weiteren hinzu.

Nginx verwirft geerbte `add_header`-Angaben in jedem Block, der eigene setzt. Neue `location`-Blöcke mit `add_header` müssen deshalb das Snippet einbinden.

### Richtlinie

```text
default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:;
font-src 'self' data:; connect-src 'self'; worker-src 'self' blob:; frame-src 'self' blob:;
manifest-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none';
report-uri /api/v1/security/csp-report/
```

- Skripte nur vom eigenen Ursprung, kein `unsafe-inline`, kein `unsafe-eval`. Monaco-Editor und seine Worker sind mitgebündelt; keine Inhalte von Fremd-CDNs.
- `'unsafe-inline'` nur für Styles: PrimeVue und Monaco erzeugen `<style>`-Elemente zur Laufzeit, bereinigter Rich Text behält `style`-Attribute. Eine Nonce bräuchte eine Nonce je Antwort in der von Nginx ausgelieferten `index.html` und deckte die `style`-Attribute nicht ab.
- `data:`/`blob:` für eingebettete Bilder und Schriften sowie die Vorschau privater Dateien (PDF, Bilder) und Worker.
- Die Richtlinie steht zweimal: `CSP_DIRECTIVES` in `backend/jf_manager_backend/settings.py` und `$jf_csp_policy` in `frontend/nginx.conf`. Der Test `api_tests.test_csp_policy` prüft, dass beide gleich sind.
- Eigene, strengere Richtlinien einzelner Antworten bleiben erhalten (private Dateien: `sandbox; default-src 'none'`; E-Mail-Vorschau im iframe zusätzlich per `<meta>`).

Verstöße meldet der Browser an `/api/v1/security/csp-report/`; das Backend protokolliert sie im Logger `security.csp` nur mit Direktive, Herkunft der blockierten Quelle und Seitenpfad (ohne Abfrageparameter), höchstens 120 Meldungen pro Minute.

### Schalter für die Fehlersuche: nur melden statt blockieren

Blockiert die CSP nach einem Update eine Funktion, lässt sie sich vorübergehend auf `Content-Security-Policy-Report-Only` umstellen. Der Browser führt dann alles aus und meldet nur.

```sh
jfctl config set CSP_REPORT_ONLY true
jfctl restart
# Meldungen ansehen
jfctl logs backend | grep "CSP violation"
# danach wieder durchsetzen
jfctl config set CSP_REPORT_ONLY false
jfctl restart
```

`CSP_REPORT_ONLY` steht in `/etc/jf-manager/app.env` und schaltet das Backend. `jfctl config set` schreibt zusätzlich `/etc/jf-manager/csp-mode.conf` (`default enforce;` oder `default report-only;`) für Nginx: im Compose-Betrieb als Datei in den Frontend-Container eingehängt, nativ direkt eingebunden. Nach `jfctl config edit` wird die Datei erst beim nächsten `jfctl config set` oder Update neu geschrieben; deshalb den Schalter mit `config set` ändern. Ein Frontend-Image ohne jfctl setzt die CSP immer durch (`frontend/csp-mode.conf`).

Im Entwicklungsmodus (`npm run dev`) liefert Vite die Oberfläche ohne CSP aus, damit HMR funktioniert; nur die über den Proxy geholten Backend-Antworten tragen die Richtlinie. Die Fehlerseite von Django im `DEBUG`-Modus funktioniert ohne Inline-Skripte nur eingeschränkt (Aufklappen); zum Prüfen der Richtlinie den Produktionsbuild hinter Nginx verwenden.

## Gemeinsamer Cache (Redis) ist Pflicht

Anmelde-, MFA- und Passwortlimits, die OIDC-Einmalmarken und das Limit für CSP-Meldungen liegen im Django-Standard-Cache. Ohne `REDIS_URL` wäre das ein Cache je Serverprozess: Limits würden mit der Zahl der Prozesse vervielfacht, eine OIDC-Marke ließe sich je Prozess einmal einlösen.

`check --deploy` meldet in diesem Fall den Fehler `users.E001`. Der Backend-Container führt `check --deploy --fail-level ERROR` vor jedem Start aus und startet ohne gemeinsamen Cache nicht. Alle mitgelieferten Compose-Dateien setzen `REDIS_URL=redis://redis:6379`.

Redis läuft mit `maxmemory 256mb` und `allkeys-lru`. Unter Speicherdruck kann Redis Limitzähler vorzeitig verwerfen; Redis deshalb nicht mit anderen Anwendungen teilen und die Speichernutzung beobachten.
