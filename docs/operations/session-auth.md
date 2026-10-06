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

Normale Konten bleiben lange angemeldet. Konten mit verpflichtender Zwei-Faktor-Anmeldung (siehe unten) erhalten eine kurze Sitzung. Aktionen, die Zugriffe erweitern, verlangen unabhängig davon eine frische Bestätigung.

| Variable | Standard | Zulässiger Bereich |
| --- | --- | --- |
| `SESSION_IDLE_TIMEOUT_SECONDS` | 2592000 (30 Tage Inaktivität) | 300–7776000 |
| `SESSION_MAX_AGE_SECONDS` | 7776000 (90 Tage ab Anmeldung) | 3600–31536000 |
| `PRIVILEGED_SESSION_IDLE_TIMEOUT_SECONDS` | 28800 (8 h Inaktivität) | 300–86400 |
| `PRIVILEGED_SESSION_MAX_AGE_SECONDS` | 28800 (8 h ab Anmeldung) | 3600–604800 |

Werte außerhalb des Bereichs werden auf die Grenze gesetzt. Erhält ein Konto während einer Sitzung Administrationsrechte, gilt spätestens nach fünf Minuten das kurze Profil. Liegt die Anmeldung dann schon länger als 8 Stunden zurück, endet die Sitzung. Die Oberfläche warnt zwei Minuten vor dem Ablauf. Statusabfragen verlängern die Sitzung nicht.

## Angemeldete Geräte

Im Profil sieht jede Person ihre aktiven Sitzungen (gekürzte Browserkennung, Anmeldezeit, letzte Aktivität). Sie kann einzelne Geräte oder alle anderen abmelden. Gespeichert wird keine IP-Adresse. Einträge verschwinden mit der zugehörigen Sitzung.

`python manage.py clearsessions` täglich ausführen. Der Befehl entfernt abgelaufene Sitzungen und damit auch deren Geräteeinträge. Bei 90-tägigen Sitzungen wächst die Tabelle sonst unnötig.

## Bestätigung für rechteerweiternde Aktionen (Step-up)

Folgende Aktionen verlangen eine höchstens fünf Minuten alte Bestätigung mit Passwort und, falls eingerichtet, zweitem Faktor. Eine frische Anmeldung zählt ebenfalls als Bestätigung.

- Schreibzugriffe auf Benutzer-, Gruppen-, Abteilungsrollen-, Rollenvorlagen- und Abteilungsverwaltung (`/api/v1/admin/…`, `/api/v1/departments/`)
- Änderungen an E-Mail-, LDAP- und OIDC-Einstellungen sowie an LDAP-/OIDC-Zuordnungen
- MFA einrichten, Wiederherstellungscodes erneuern, MFA deaktivieren
- XLSX-Exporte von Mitgliedern und Listen (abgewiesene Versuche erscheinen im Exportaudit mit 403)

Die Oberfläche zeigt dafür einen Dialog und wiederholt die Aktion nach der Bestätigung automatisch. SSO-Konten ohne eigenes MFA melden sich zur Bestätigung erneut beim Provider an. Passwortwechsel verlangt ohnehin das bisherige Passwort.

## Zwei-Faktor-Anmeldung (Passkey oder Authenticator-App)

Als zweiter Faktor nach Passwort bzw. SSO dienen **Passkeys** (WebAuthn: Fingerabdruck, Gesichtserkennung, Geräte-PIN, Sicherheitsschlüssel, Passwortmanager) und/oder eine **Authenticator-App** (TOTP). Beides lässt sich im Profil parallel einrichten; ein Konto kann bis zu zehn Passkeys haben.

Verpflichtend für Superuser, Staff (Django-Admin), Konten mit Rechten zur Benutzer-, Gruppen-, Rollen-, Abteilungs- oder Sicherheitseinstellungsverwaltung sowie die Rollenvorlagen Jugendwart, Abteilungsjugendwart und Systemadministration. Solche Konten erreichen nach dem Login nur die Einrichtung im Profil, bis MFA aktiv ist. Alle anderen Konten können MFA freiwillig einrichten.

- Jeder TOTP-Code gilt nur einmal. Die zehn Wiederherstellungscodes werden mit dem ersten Faktor ausgegeben, gelten jeweils einmal (auch für Konten nur mit Passkeys) und werden nur gehasht gespeichert.
- Das TOTP-Geheimnis ist mit dem Feldschlüssel verschlüsselt. `rotate_field_encryption` schließt es ein (siehe [encryption-rotation.md](encryption-rotation.md)). Von Passkeys speichert JF-Manager nur den öffentlichen Schlüssel und den Signaturzähler; ein Zähler, der nicht steigt, deutet auf einen kopierten Schlüssel und wird abgelehnt. Eine Attestierung (Gerätemodell) wird nicht abgefragt.
- Der letzte zweite Faktor eines Kontos mit verpflichtender MFA lässt sich nicht entfernen; zuerst einen weiteren einrichten.

### Passkeys: Domain und HTTPS

Passkeys sind an die Adresse der Oberfläche gebunden. Relying-Party-ID und erlaubte Herkunft ergeben sich aus `FRONTEND_URL` (z. B. `https://jf.example.org` → RP-ID `jf.example.org`). Abweichend setzbar:

| Variable | Wirkung |
| --- | --- |
| `WEBAUTHN_RP_ID` | RP-ID, z. B. `example.org`, damit Passkeys auf allen Subdomains gelten |
| `WEBAUTHN_ORIGINS` | Kommagetrennte erlaubte Herkünfte, z. B. `https://jf.example.org,https://www.jf.example.org` |

Browser erlauben Passkeys nur über HTTPS (Ausnahme `http://localhost` für die Entwicklung). **Ändert sich die Domain, funktionieren bestehende Passkeys nicht mehr**; betroffene Personen melden sich mit Authenticator-App oder Wiederherstellungscode an oder ihre MFA wird zurückgesetzt (siehe unten).

### Zwei-Faktor-Anmeldung zurücksetzen

Für Personen, die Passkey, App und Wiederherstellungscodes verloren haben. Das Zurücksetzen entfernt Authenticator-App, alle Passkeys und Wiederherstellungscodes und beendet alle Sitzungen des Kontos; bei der nächsten Anmeldung wird MFA neu eingerichtet (bei Pflichtkonten ist bis dahin nur die Einrichtung erreichbar). Vorher die Identität der Person auf einem anderen Weg prüfen.

- **Weboberfläche (normale Konten):** Superuser öffnen *Administration → Benutzer*, wählen das Konto und nutzen *Zwei-Faktor-Anmeldung zurücksetzen* (mit Bestätigung und Step-up).
- **Konsole (alle Konten, einzig für Administrationskonten):** Für Superuser, Staff und alle Konten mit verpflichtender MFA lehnt die Oberfläche das Zurücksetzen ab, damit eine übernommene Admin-Sitzung anderen Admins nicht den zweiten Faktor entziehen kann. Auf dem Server:

  ```sh
  sudo jfctl admin reset-mfa --user NAME       # nur zweiter Faktor
  sudo jfctl admin recover --user NAME --reset-mfa   # zusätzlich neues Passwort
  ```

  Ohne `jfctl` (Entwicklung): `python manage.py reset_mfa --user NAME`.

Jedes Zurücksetzen wird im Logger `security.mfa` mit Konto-ID, ausführender Konto-ID und Kanal (`console`, `admin-ui`) protokolliert, ohne Namen.

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
