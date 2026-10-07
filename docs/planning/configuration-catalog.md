# Konfigurationskatalog und Quellenvertrag

Stand: 07.10.2026. CFG-01 ist implementiert, abgenommen und separat committed; Prüfstand und Betriebsgrenzen siehe Roadmap. Keine echten Konfigurationswerte sind in diesem Katalog enthalten.

## Verbindlicher Vertrag

- Fachliche Einstellungen haben eine DB-Quelle. Hostverbindungen, Domain/TLS, Pfade und Hauptschlüssel bleiben Hostkonfiguration.
- Lesen benötigt das globale `settings_manager.view_<kategorie>_settings` oder `view_all_settings`; Schreiben das entsprechende `change`-Recht. Abteilungsrollen erweitern keine globalen Konfigurationsrechte. Administrative Sicherheits-/Integrationsänderungen benötigen MFA und Step-up ≤ 5 Minuten.
- Geheimnisse werden ausschließlich geschrieben; Antworten enthalten höchstens einen Vorhanden-Status. Weglassen erhält den Wert; ausdrücklich leer setzen entfernt ihn. Keine Rückgabe über Katalog, Fehler oder Diagnosen.
- Teilupdates validieren den Gesamtzustand und speichern atomar. Unbekannte Felder werden zurückgewiesen. Verbindungen werden erst beim ausdrücklichen Test geprüft; Test-E-Mails sind eine eigene Aktion.
- Für jedes Feld nennt die Metadaten-API Quelle, Speicher, effektive Validierung, Schreibbarkeit und Wirksamkeit. Erlaubte Umgebungsüberschreibungen werden gesperrt angezeigt; gesperrte Updates werden zurückgewiesen.

## Bestehende Einstellungsfelder

### general

API: `/api/v1/settings/general/`. Speicher: GlobalPreferenceModel: general__*. Fachrecht: `view/change_general_settings` oder `view/change_all_settings`. Wirksam: nächste Anfrage; Zeit-/Standardwerte nur für neue Datensätze, Integrationen beim nächsten Login/Verbindungsaufbau. Keine Umgebungsüberschreibung für diese bestehenden Felder.

| Feld | Validierung | Ausgabe |
| --- | --- | --- |
| `title` | CharField; max_length=200, allow_blank=True | lesen/schreiben |
| `slug` | CharField; max_length=100, allow_blank=True | lesen/schreiben |
| `logo_url` | URLField; allow_blank=True | lesen/schreiben |
| `brand_color` | RegexField; error_messages={'invalid': 'Bitte eine Farbe im Format #rrggbb angeben.'} | lesen/schreiben |

### email

API: `/api/v1/settings/email/`. Speicher: GlobalPreferenceModel: email__*; Passwort ab CFG-01.2 verschlüsselt. Fachrecht: `view/change_email_settings` oder `view/change_all_settings`. Wirksam: nächste Anfrage; Zeit-/Standardwerte nur für neue Datensätze, Integrationen beim nächsten Login/Verbindungsaufbau. Keine Umgebungsüberschreibung für diese bestehenden Felder.

| Feld | Validierung | Ausgabe |
| --- | --- | --- |
| `email_host` | CharField; max_length=200, allow_blank=True | lesen/schreiben |
| `email_port` | IntegerField; min_value=1, max_value=65535 | lesen/schreiben |
| `email_use_tls` | BooleanField; typabhängige Validierung | lesen/schreiben |
| `email_use_ssl` | BooleanField; typabhängige Validierung | lesen/schreiben |
| `email_host_user` | CharField; max_length=200, allow_blank=True | lesen/schreiben |
| `email_host_password` | CharField; allow_blank=True | nur schreiben, verschlüsselt |
| `default_from_email` | EmailField; allow_blank=True | lesen/schreiben |

### member

API: `/api/v1/settings/member/`. Speicher: GlobalPreferenceModel: members__*. Fachrecht: `view/change_member_settings` oder `view/change_all_settings`. Wirksam: nächste Anfrage; Zeit-/Standardwerte nur für neue Datensätze, Integrationen beim nächsten Login/Verbindungsaufbau. Keine Umgebungsüberschreibung für diese bestehenden Felder.

| Feld | Validierung | Ausgabe |
| --- | --- | --- |
| `alert_threshold` | IntegerField; min_value=1 | lesen/schreiben |
| `alert_threshold_last_entries` | IntegerField; min_value=1 | lesen/schreiben |

### service

API: `/api/v1/settings/service/`. Speicher: GlobalPreferenceModel: service__*. Fachrecht: `view/change_service_settings` oder `view/change_all_settings`. Wirksam: nächste Anfrage; Zeit-/Standardwerte nur für neue Datensätze, Integrationen beim nächsten Login/Verbindungsaufbau. Keine Umgebungsüberschreibung für diese bestehenden Felder.

| Feld | Validierung | Ausgabe |
| --- | --- | --- |
| `service_start_time` | TimeField; typabhängige Validierung | lesen/schreiben |
| `service_end_time` | TimeField; typabhängige Validierung | lesen/schreiben |

### order

API: `/api/v1/settings/order/`. Speicher: GlobalPreferenceModel: orders__*. Fachrecht: `view/change_order_settings` oder `view/change_all_settings`. Wirksam: nächste Anfrage; Zeit-/Standardwerte nur für neue Datensätze, Integrationen beim nächsten Login/Verbindungsaufbau. Keine Umgebungsüberschreibung für diese bestehenden Felder.

| Feld | Validierung | Ausgabe |
| --- | --- | --- |
| `equipment_manager_email` | EmailField; allow_blank=True | lesen/schreiben |

### ldap

API: `/api/v1/settings/ldap/`. Speicher: LDAPConfig (Singleton). Fachrecht: `view/change_ldap_settings` oder `view/change_all_settings`. Wirksam: nächste Anfrage; Zeit-/Standardwerte nur für neue Datensätze, Integrationen beim nächsten Login/Verbindungsaufbau. Keine Umgebungsüberschreibung für diese bestehenden Felder.

| Feld | Validierung | Ausgabe |
| --- | --- | --- |
| `enabled` | BooleanField; typabhängige Validierung | lesen/schreiben |
| `server_uri` | CharField; allow_blank=True, max_length=255 | lesen/schreiben |
| `start_tls` | BooleanField; typabhängige Validierung | lesen/schreiben |
| `ca_cert_file` | CharField; allow_blank=True, max_length=512 | lesen/schreiben |
| `ca_cert_content` | CharField; allow_blank=True | lesen/schreiben |
| `disable_cert_validation` | BooleanField; typabhängige Validierung | lesen/schreiben |
| `bind_dn` | CharField; allow_blank=True, max_length=255 | lesen/schreiben |
| `bind_password` | CharField; allow_blank=True | nur schreiben, verschlüsselt |
| `has_bind_password` | BooleanField; typabhängige Validierung | nur lesen (Status) |
| `user_search_base_dn` | CharField; allow_blank=True, max_length=255 | lesen/schreiben |
| `user_search_filter` | CharField; allow_blank=True, max_length=255 | lesen/schreiben |
| `group_search_base_dn` | CharField; allow_blank=True, max_length=255 | lesen/schreiben |
| `group_search_filter` | CharField; allow_blank=True, max_length=255 | lesen/schreiben |
| `group_type` | ChoiceField; choices=['group_of_names', 'active_directory'] | lesen/schreiben |
| `mirror_groups` | BooleanField; typabhängige Validierung | lesen/schreiben |
| `require_group` | CharField; allow_blank=True, max_length=255 | lesen/schreiben |

### oidc

API: `/api/v1/settings/oidc/`. Speicher: OIDCConfig (Singleton). Fachrecht: `view/change_oidc_settings` oder `view/change_all_settings`. Wirksam: nächste Anfrage; Zeit-/Standardwerte nur für neue Datensätze, Integrationen beim nächsten Login/Verbindungsaufbau. Keine Umgebungsüberschreibung für diese bestehenden Felder.

| Feld | Validierung | Ausgabe |
| --- | --- | --- |
| `enabled` | BooleanField; typabhängige Validierung | lesen/schreiben |
| `provider_name` | CharField; allow_blank=True, max_length=100 | lesen/schreiben |
| `issuer_url` | CharField; allow_blank=True, max_length=500 | lesen/schreiben |
| `client_id` | CharField; allow_blank=True, max_length=255 | lesen/schreiben |
| `client_secret` | CharField; allow_blank=True | nur schreiben, verschlüsselt |
| `has_client_secret` | BooleanField; typabhängige Validierung | nur lesen (Status) |
| `callback_url` | CharField; typabhängige Validierung | nur lesen (Status) |
| `scope` | CharField; allow_blank=True, max_length=255 | lesen/schreiben |
| `groups_claim` | CharField; allow_blank=True, max_length=100 | lesen/schreiben |
| `staff_group` | CharField; allow_blank=True, max_length=255 | lesen/schreiben |
| `admin_group` | CharField; allow_blank=True, max_length=255 | lesen/schreiben |
| `require_group_mapping` | BooleanField; typabhängige Validierung | lesen/schreiben |
| `hide_local_login` | BooleanField; typabhängige Validierung | lesen/schreiben |
| `trust_provider_mfa` | BooleanField; typabhängige Validierung | lesen/schreiben |

## Metadaten, Einrichtung und sichere Tests

`GET /settings/catalog/` liefert den berechtigungsgefilterten Feldvertrag ohne Werte:
Quelle (`database`, `default`, `environment` oder `computed`), Speicherung, Sperre,
Geheimnisstatus, Typ/Grenzen, Validierung und Wirksamkeit sowie Kategoriepermissions.
Vorhanden-Status und OIDC-Rücksprungadresse sind abgeleitete Felder.
`GET /settings/setup/` liefert nur aggregierten Einrichtungsstand für globale Einstellungssicht.
`GET /settings/client-defaults/` liefert authentifizierten Konten ausschließlich harmlose
Organisations-/Zeit-/Vokabularwerte; SMTP-/Anmeldegeheimnisse sind ausgeschlossen.

`POST /settings/email/test-connection/` öffnet/schließt SMTP ohne Nachricht;
`POST /settings/email/send-test/` verlangt `recipient` und `confirm_send: true`.
Beide verlangen globales E-Mail-Änderungsrecht und Step-up. LDAP-Tests suchen nur;
OIDC-Discovery liest nur. Keine Testfunktion importiert oder verändert Fachdaten.

SMTP-Antworten enthalten `has_email_host_password` und `email_credentials_unavailable`.
Weggelassene Passwörter bleiben erhalten; ein ausdrücklich leeres Passwort entfernt sie.
Im expliziten lokalen Wiederherstellungsmodus (`DEBUG=True` und
`DEV_ALLOW_UNREADABLE_SMTP=True`) startet die Webanwendung bei unlesbarem SMTP-Passwort
mit gesperrtem Versand. Produktionsbetrieb sowie MFA-/LDAP-/OIDC-/Sync-Dekodierung bleiben
strikt. Das Geheimnis wird nicht gelöscht. Worker prüfen DB-Zugangsdaten beim Öffnen der
SMTP-Verbindung und fallen nicht auf Umgebungspasswörter zurück.

## Erweiterungen CFG-01

| Bereich/Feld | Quelle und Speicher | Validierung | Recht / Wirksamkeit |
| --- | --- | --- | --- |
| Sicherheitsrichtlinien: `session_idle_timeout_seconds`, `session_max_age_seconds`, `privileged_session_idle_timeout_seconds`, `privileged_session_max_age_seconds` | DB-Konfiguration; gleichnamige Großbuchstaben-Umgebung überschreibt und sperrt | Normale Inaktivität 300–7776000 s, Höchstdauer 3600–31536000 s; privilegiert 300–86400 bzw. 3600–604800 s; Inaktivität ≤ Höchstdauer | Globale Einstellungssicht/-änderung plus Step-up; nächste Sitzungsprüfung |
| Push: `enabled`, `public_key`, `private_key`, `subject` | DB-Konfiguration; VAPID-Triplett bei Hostvorgabe vollständig gesperrt | EC-P256-Schlüsselpaar, passende öffentliche/private Schlüssel, `mailto:`- oder HTTPS-Kontakt; Aktivierung nur bei vollständiger Konfiguration | Globale Einstellungssicht/-änderung plus Step-up; nächster Pushvorgang |
| Übungsstandards: Start-/Endzeit, Bausteindauer | DB-Preferences | HH:MM, Start < Ende, Dauer 1–480 min | Globale allgemeine Konfiguration; nur Neuanlage |
| Organisationsbegriffe `member_label`, `service_label`, `training_label` | DB-Preferences in `general`; API `vocabulary` | nicht leer, höchstens 80 Zeichen | Allgemeine Konfiguration; nächste UI-Aktualisierung |

## Vorhandene Webverwaltungen und Einrichtungsassistent

| Aufgabe | Datenquelle | Fachliche Berechtigung / Verwaltung |
| --- | --- | --- |
| Organisation und Branding | general-Preferences | `/settings/general` |
| Abteilungen | Department | `/departments`, globale Abteilungsverwaltung |
| Konten und Rollen | CustomUser, Group, RoleTemplate, UserDepartmentRole, RoleGrant | `/users`, `/roles`, `/role-templates`; ROLE-Rechtevertrag, MFA/Step-up |
| Mitgliedergruppen, Status und Ereignisarten | MemberGroup/Status/EventType | Mitglieder-/Einstellungsverwaltung; passende Modellrechte, zentrale Stammdaten nur global |
| Qualifikations-/Aufgabentypen | QualificationType/SpecialTaskType | Qualifikationsverwaltung; passende globale Modellrechte |
| Inventar- und Bestellstammdaten/Workflows | Category/Item/StorageLocation/OrderStatus/OrderableItem/EmailTemplate | Inventar-/Bestellverwaltung, passende globale Modellrechte |
| Übungs-/Bibliotheksvorlagen | TrainingTemplate/LibraryBlock und Kategorien/Tags | Trainingsverwaltung/Bibliothek; fachliche Rechte |
| LDAP-/OIDC-Rollenmappings | LDAPDepartmentRoleMapping/OIDCGroupMapping | Einstellungsverwaltung plus administratives Rollenzuweisungsrecht |
| Externer Datenabgleich | SyncJob/SyncBinding/SyncRun | Mitglieder-Sync-Verwaltung, explizite Modell-/Ausführungsrechte |

Der Assistent verbindet diese Webverwaltungen, prüft den Einrichtungsstand und erklärt optionale Schritte. Er erzeugt keine stillen Rollenzuweisungen und ersetzt nicht die expliziten Vorschau-/Freigabeaktionen.

## Hostkonfiguration bleibt getrennt

| Werte | Herkunft | Veränderung / Anzeige |
| --- | --- | --- |
| Domain, Ports, Proxy-Vertrauen, TLS/HSTS, erlaubte Hosts/Origins | Umgebung/Host-CLI | nur Betrieb; Interface zeigt Herkunft, keine geheime Verbindungszeichenfolge |
| DB-/Redis-Verbindung, Dateisystempfade und Release-/Containerkonfiguration | Umgebung/Host-CLI | nur Betrieb |
| Django-Geheimnis und Verschlüsselungsschlüsselring | Umgebung/Host-CLI | nur vorhandener Status, niemals Werte; Backup/Restore muss Schlüssel erhalten |
| Backupziel/Entschlüsselung und Notfallbootstrap | Host-CLI | kein Webschreiben; OPS-Vertrag |

## Prüfvertrag

Kategorie-/Modellrechte, Step-up, Schreibgeheimnisse, Bestandsmigration und Schlüsselrotation; atomare Teilupdates einschließlich TLS/SSL und Zeitpaaren; Umgebungsvorrang/-sperren; tatsächlich wirksame Sitzung/Push-/Neuanlagewerte; keine Echtdaten bei Verbindungstests. Frontend: lesbare Felder, gesperrte Herkunft, Fehler erhalten Eingaben, verständlicher Assistent.
