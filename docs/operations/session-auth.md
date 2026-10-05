# Anmeldung: Sitzungen, MFA und SSO

Ab diesem Release meldet sich die Weboberfläche ausschließlich über ein serverseitiges Sitzungscookie an. JWT- und DRF-Token-Zugänge sind entfernt. Externe API-Programme, die solche Tokens nutzten, funktionieren nicht mehr.

## Vor dem Update

1. Datenbank sichern.
2. Oberfläche und API müssen unter **derselben Herkunft** laufen (gleiches Schema, gleicher Host, gleicher Port). Der mitgelieferte Nginx leitet `/api/` an das Backend weiter; `VITE_API_BASE_URL` bleibt `/api/v1`. Eine getrennte API-Domain wird nicht unterstützt.
3. `FRONTEND_URL` auf die öffentliche Adresse setzen (Ziel für Admin- und SSO-Weiterleitungen).
4. Bei HTTPS hinter einem Reverse Proxy muss dieser `X-Forwarded-Proto: https` setzen. Cookies sind standardmäßig `Secure`. Nur für lokale Entwicklung ohne HTTPS: `SECURE_COOKIES=false`.
5. Konten mit verpflichtender Zwei-Faktor-Anmeldung vorab informieren (siehe unten). Sie brauchen beim ersten Login eine Authenticator-App.

## Update

`python manage.py migrate` führt `users.0010_retire_legacy_tokens` aus:

- Alle bestehenden Sitzungen werden beendet. Jede Person muss sich neu anmelden.
- Die Tabellen der alten JWT-Sperrliste und der DRF-Tokens werden gelöscht. Bereits ausgegebene Tokens sind damit wertlos. Der Schritt kann nicht zurückgenommen werden. Für ein Zurück zur Vorversion das Backup wiederherstellen.

Proxy- und CDN-Caches müssen keine Anmeldedaten enthalten. Falls doch, leeren.

## Sitzungsdauer

| Variable | Standard | Zulässiger Bereich |
| --- | --- | --- |
| `SESSION_IDLE_TIMEOUT_SECONDS` | 1800 (30 min Inaktivität) | 300–14400 |
| `SESSION_MAX_AGE_SECONDS` | 43200 (12 h ab Anmeldung) | 3600–86400 |

Werte außerhalb des Bereichs werden auf die Grenze gesetzt. Die Oberfläche warnt zwei Minuten vor dem Ablauf. Statusabfragen verlängern die Sitzung nicht.

## Zwei-Faktor-Anmeldung (TOTP)

Verpflichtend für Superuser, Staff (Django-Admin), Konten mit Rechten zur Benutzer-, Gruppen-, Rollen-, Abteilungs- oder Sicherheitseinstellungsverwaltung sowie die Rollenvorlagen Jugendwart, Abteilungsjugendwart und Systemadministration. Solche Konten erreichen nach dem Login nur die Einrichtung im Profil, bis MFA aktiv ist. Alle anderen Konten können MFA freiwillig einrichten.

- Einrichtung, neue Wiederherstellungscodes und Deaktivierung verlangen eine höchstens fünf Minuten alte Bestätigung mit Passwort und gegebenenfalls Code.
- Jeder TOTP-Code gilt nur einmal. Die zehn Wiederherstellungscodes gelten jeweils einmal und werden nur gehasht gespeichert.
- Das TOTP-Geheimnis ist mit dem Feldschlüssel verschlüsselt. `rotate_field_encryption` schließt es ein (siehe [encryption-rotation.md](encryption-rotation.md)).

**Verlorener Authenticator ohne Wiederherstellungscode:** Eine Systemadministration entfernt im Django-Admin oder per Shell den Eintrag *MFA-Gerät* des Kontos. Danach richtet die Person MFA beim nächsten Login neu ein. Den Vorgang dokumentieren.

## Django-Admin

`/admin/login/` leitet auf die normale Anmeldung (`/login?next=/admin/`). Damit gelten Drosselung und MFA auch hier. Die bisherigen Formulare unter `/accounts/` und `/api-auth/` sind entfernt.

## SSO (OIDC)

- Die Redirect-URI beim Provider bleibt `https://<host>/api/v1/auth/oidc/callback/`.
- JF-Manager nutzt PKCE (S256). Der Provider muss es unterstützen; das ist bei aktuellen Versionen von Keycloak, Authentik, Nextcloud und Entra ID der Fall.
- Authorization- und Token-Endpunkt müssen per HTTPS auf demselben Host wie die Issuer-URL liegen.
- Fehlermeldungen in der Oberfläche enthalten keine Personendaten mehr. Details stehen im Serverprotokoll (nur Benutzer-ID und Fehlertyp).
- **MFA des Providers anerkennen** (OIDC-Einstellungen) nur aktivieren, wenn der Provider einen zweiten Faktor erzwingt und im ID-Token per `amr` meldet (z. B. `mfa`, `otp`, `hwk`). Sonst verlangt JF-Manager für MFA-pflichtige Konten zusätzlich den eigenen Code.

## Entwicklung

`npm run dev` leitet `/api`, `/admin` und `/static` an `VITE_BACKEND_URL` weiter (Standard `http://localhost:8000`). `VITE_API_BASE_URL` nicht auf eine absolute Backend-Adresse setzen, sonst fehlen Sitzungs- und CSRF-Cookies. Backend mit `DEBUG=True` setzt Cookies ohne `Secure`.
