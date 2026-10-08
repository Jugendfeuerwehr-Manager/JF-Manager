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

Der Nginx im Frontend-Container setzt die Header über zwei Snippets in `/etc/nginx/snippets/` (Quelle: `frontend/snippets/`):

- `security-headers.conf` für alles, was Nginx selbst ausliefert (Oberfläche, Assets, `/static/`, Service Worker, Manifest): `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin`, `Cross-Origin-Opener-Policy: same-origin` sowie die CSP-Zeilen.
- `csp-report-only.conf` für `/api/` und `/admin/`; die übrigen Header setzt dort Django.

Nginx verwirft geerbte `add_header`-Angaben in jedem Block, der eigene setzt. Neue `location`-Blöcke mit `add_header` müssen deshalb das passende Snippet einbinden.

Die CSP läuft zunächst als `Content-Security-Policy-Report-Only`. Verstöße meldet der Browser an `/api/v1/security/csp-report/`; das Backend protokolliert sie im Logger `security.csp` nur mit Direktive, Herkunft der blockierten Quelle und Seitenpfad (ohne Abfrageparameter), höchstens 120 Meldungen pro Minute.

Umstellung auf Durchsetzung: Nach einer Beobachtungsphase ohne unerwartete Meldungen in `csp-report-only.conf` den Headernamen auf `Content-Security-Policy` ändern und das Image neu bauen.

## Gemeinsamer Cache (Redis) ist Pflicht

Anmelde-, MFA- und Passwortlimits, die OIDC-Einmalmarken und das Limit für CSP-Meldungen liegen im Django-Standard-Cache. Ohne `REDIS_URL` wäre das ein Cache je Serverprozess: Limits würden mit der Zahl der Prozesse vervielfacht, eine OIDC-Marke ließe sich je Prozess einmal einlösen.

`check --deploy` meldet in diesem Fall den Fehler `users.E001`. Der Backend-Container führt `check --deploy --fail-level ERROR` vor jedem Start aus und startet ohne gemeinsamen Cache nicht. Alle mitgelieferten Compose-Dateien setzen `REDIS_URL=redis://redis:6379`.

Redis läuft mit `maxmemory 256mb` und `allkeys-lru`. Unter Speicherdruck kann Redis Limitzähler vorzeitig verwerfen; Redis deshalb nicht mit anderen Anwendungen teilen und die Speichernutzung beobachten.
