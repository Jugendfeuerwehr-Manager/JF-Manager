# JF-Manager

**Mehr Zeit für eure Jugendfeuerwehr.** JF-Manager bringt Mitglieder, Eltern, Dienste, Ausbildung und Ausstattung an einen Ort. Jugendleiterinnen und Jugendleiter können Anwesenheiten gemeinsam erfassen; die Anwendung ist auf dem Smartphone als Web-App installierbar.

![JF-Manager: Übersicht mit dauerhaft sichtbarer Modulnavigation und fiktiven Beispieldaten](docs/images/dashboard.png)

Die Abbildungen stammen aus einer eigens erzeugten Demo mit **ausschließlich fiktiven Daten**. [Benutzerhandbuch](docs/user-guide.md) · [Installation](#installation) · [Mitmachen](CONTRIBUTING.md)

## Was ihr damit erledigt

| Alltag | Im JF-Manager |
| --- | --- |
| Mitglieder begleiten | Stammdaten, Gruppen, Elternkontakte, Notizen, Anhänge und auswählbare Excel-Exporte |
| Dienste dokumentieren | Termine, Themen, Übungsleitung, besondere Vorkommnisse und Anwesenheiten |
| Gemeinsam abhaken | Jugendliche und Betreuungspersonen getrennt erfassen; Änderungen einzelner Personen sofort speichern und alle drei Sekunden abgleichen |
| Betreuungsarbeit auswerten | Anwesenheit von Jugendleitern/Ausbildern nach Zeitraum und geleisteten Stunden auswerten |
| Ausbildung planen | Ausbildungskalender, wiederkehrende Termine, Planer, Bausteinbibliothek und Handouts |
| Ausstattung verwalten | Inventar, Lagerorte, Ausleihen, Barcode-Erfassung und Bestellabläufe |
| Kommunikation organisieren | Listen mit Check-Workflow, E-Mails, Versandhistorie und Benachrichtigungen für Dienst- und Bestellereignisse |
| Verantwortlichkeiten abbilden | Abteilungen, Rollen, Qualifikationen, Sonderaufgaben, LDAP und OIDC-SSO |

Die Modulnavigation ist auf dem Desktop dauerhaft sichtbar und durchsuchbar. Mobil führen **Module** und **Alle Module** zur vollständigen Übersicht.

![Anwesenheit von Jugendleitern und Ausbildern im Dienstbuch](docs/images/attendance.png)

Beim Abhaken wird nur die ausgewählte Person gespeichert. Bearbeiten zwei Personen gleichzeitig denselben Eintrag, fordert die Anwendung zur Prüfung des aktuellen Stands auf. Die Team-Auswertung zählt anwesend, entschuldigt und fehlend sowie Stunden aus der Dienstdauer. [Schrittweise Anleitung im Handbuch](docs/user-guide.md#dienstbuch-und-gemeinsame-anwesenheitserfassung)

![Alle Module in der mobilen Web-App](docs/images/mobile.png)

Die Web-App lässt sich unter HTTPS zum Startbildschirm hinzufügen. Push-Mitteilungen werden **pro Gerät freiwillig** im Profil aktiviert; wählbar sind Dienste und Bestellungen. Der Sperrbildschirm zeigt allgemeine Hinweise ohne Mitgliedernamen. Für Datenzugriff und Änderungen ist eine Internetverbindung nötig. [Einrichtung und technische Grenzen](docs/push-and-pwa.md)

## Installation

Unterstützt werden zwei Produktionswege mit demselben Verwaltungswerkzeug `jfctl`: **Docker Compose** mit vorgebauten, versionsgebundenen Images und **Debian 13 nativ** (auch in einem Proxmox-LXC). HTTPS richtet `jfctl` mit Caddy selbst ein oder übergibt an einen vorhandenen Reverse Proxy. Vor dem Einsatz mit echten Mitgliederdaten [Produktionsvorgaben](docs/operations/production-security.md) lesen.

```sh
VERSION=1.4.0   # gewünschtes Release
BASE=https://github.com/Jugendfeuerwehr-Manager/JF-Manager/releases/download/v$VERSION
curl -fsSLO "$BASE/jf-manager-$VERSION.tar.gz" -O "$BASE/SHA256SUMS" -O "$BASE/release-manifest.json"
sha256sum -c SHA256SUMS && tar -xzf "jf-manager-$VERSION.tar.gz"
sudo "./jf-manager-$VERSION/ops/jfctl" install --version "$VERSION" --release-dir .
```

Der Assistent fragt alle Angaben vorab ab, prüft das System und installiert erst nach Bestätigung. Danach: `jfctl status`, `jfctl doctor`, `jfctl backup create`, `jfctl update --version …`. Details: [Installation](docs/operations/ops-install.md), [Betrieb mit jfctl](docs/operations/ops-jfctl.md), [Sicherung und Updates](docs/operations/ops-backup-restore-update.md). Bestehende Compose-, Portainer- oder Synology-Installationen werden über [Migration](docs/operations/ops-migration.md) übernommen. Die `docker-compose.yml` im Projektwurzelverzeichnis dient nur der Entwicklung.

## Ausprobieren mit Beispieldaten

Die lokale Demo erzeugt eine **neue temporäre SQLite-Datenbank** mit zwölf fiktiven Mitgliedern, vier Betreuungspersonen und Beispieldiensten. Sie benutzt weder die vorhandene Anwendungsdatenbank noch echten E-Mail- oder Push-Versand. Voraussetzungen sind Python 3.12+, Pipenv und Node.js 20.19+ beziehungsweise 22.12+.

```sh
cd backend
pipenv install
pipenv run python demo.py --port 8011
```

Benutzername und zufälliges Demopasswort erscheinen im Terminal. In einem zweiten Terminal:

```sh
cd frontend
npm ci
VITE_BACKEND_URL=http://127.0.0.1:8011 npm run dev
```

Anschließend `http://localhost:5173` öffnen. Die Demo lauscht nur lokal. Für die reguläre Entwicklung stehen [Startanleitung](docs/getting-started.md), `./start-dev.sh` und die VS-Code-Startkonfiguration „JF-Manager: Backend + Frontend“ bereit. In VS Code startet „Demo: Backend + Frontend“ die Demo samt Oberfläche. Das Demokonto ist Administrator und muss beim ersten Login eine Authenticator-App einrichten.

## Einstieg für das Team

1. Persönlich anmelden; bei eingerichtetem SSO den entsprechenden Knopf verwenden.
2. Die richtige Abteilung auswählen und über die Modulnavigation **Mitglieder** und **Dienstbuch** öffnen.
3. Einen Dienst speichern, anschließend Jugendliche und Betreuungspersonen im Anwesenheitsbereich erfassen.
4. Im Profil die Standard-Abteilung, E-Mail-Signatur sowie Installation und Mitteilungen verwalten.

![Klarer Anmeldebildschirm ohne künstliche Wartezeit](docs/images/login.png)

![Geräteeinstellungen im persönlichen Profil](docs/images/profile.png)

Das [Benutzerhandbuch](docs/user-guide.md) erläutert alle Module mit praktischen Abläufen. Die [Architektur](docs/architecture/overview.md), [API-Referenz](docs/api/reference.md) und [Entwicklungsdokumentation](docs/development/build-pipeline.md) helfen bei Erweiterungen.

## Technik und Qualität

Das Backend verwendet Django 5 und Django REST Framework, das Frontend Vue 3, TypeScript und PrimeVue. PostgreSQL 17 dient als Produktionsdatenbank, Redis als gemeinsamer Cache; betrieben wird über `jfctl` mit Docker Compose oder nativ auf Debian 13. Zugriffsrechte werden für Benutzer, Abteilungen und einzelne API-Routen geprüft. [Betrieb](docs/operations/ops-overview.md)

```sh
cd backend && PIPENV_DONT_LOAD_ENV=1 DJANGO_SECRET_KEY=local-test-only-secret-key-32-chars FIELD_ENCRYPTION_KEY=$(pipenv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())") REDIS_URL=none pipenv run python manage.py test api_tests users departments.tests servicebook.tests.test_attendance_board servicebook.tests.test_attendance_by_member servicebook.tests.test_attendance_race_condition notifications
cd ../frontend && npm run build && npm run test:unit -- --run
```

JF-Manager ist unter der [GNU Affero General Public License](backend/LICENSE) veröffentlicht. Beiträge sind willkommen: [CONTRIBUTING.md](CONTRIBUTING.md).
