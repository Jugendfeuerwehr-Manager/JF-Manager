# JF-Manager

JF-Manager ist eine Webanwednung zur einfache Verwaltung deiner Jugendfeuerwehr. 

## 📝 Hisotire & Beschreibung

Das Projekt wurde von mir im Jahr 2018 begonnen, mit dem Ziel eine einfachere und unkomplizierte Webanwendung zu bauen, um meine Jugendfeuerwehr zu verwalten. 

Wir hatten vorher lediglich einige Liste in Excel und andere Verwaltungssoftware war uns zu kompliziert. 

Mit dem JF-Manager lässt sich aktuell der Dienstbetrieb einer Jugendfeuerwehr online verwalten.
Es wird stetig weiterentwickelt und um neue Funktionen ergänzt. Wie oben bereits erwähnt ist das ganze ein Hobbyprojekt und erst ganz frisch (2025) als OpenSource verfügbar - Vielleicht kann es ja noch jemand brauchen ... 


### 🎯 Hauptfunktionen

- Verwaltung von Mitgliedern
  - Export in Excel Listen
  - Erfassen von Ehrungen, Notizen, Auszeichnungen etc.
- Verwaltung von Eltern, inkl. E-Mail und verknüpfung mit den Mitgliedern
- Kleiderkammer
  - Barcode Scanner
  - Zuordnung zu den Mitgliedern
- Dienstbuch
  - Erfassen von Diensten
  - Dokumentieren von Besonderen Vorkommnissen
  - Anwesenheit erfassen und auswerten
- REST Api zur anbindung von eigenen Apps und Diensten


## 🚀 Installation & Setup

JF-Manager wurde auf Basis des Djange Frameworks (python) entwickelt. Demenentsprechen ist eine passende Hosting Umgebung erforderlich. 

Im Wiki können (bald) die verschiedenen Installationsarten nachgelsenen werden. 

Aktuell steht ein Container so wie eine Docker Compose Datei zur verfügung um die Software an den Start zu bringen. 

Alternativ dazu kann man es auch gut in einem pipenv betreiben. 

### Lokale Entwicklungsumgebung

1. Repository klonen:
```bash
git clone https://github.com/Jugendfeuerwehr-Manager/JF-Manager.git
cd JF-Manager
```

2. Python-Abhängigkeiten installieren:
```bash
pipenv install
pipenv shell
```

3. Datenbank einrichten:
```bash
python manage.py migrate
python manage.py createsuperuser
```

4. Entwicklungsserver starten:
```bash
python manage.py runserver
```

### Docker-Installation

1. Image von GitHub Packages ziehen:
```bash
docker pull ghcr.io/jugendfeuerwehr-manager/jf-manager-server:latest
```

2. Container starten (SQLite):
```bash
docker run -d \
  -e SECRET_KEY=your-secret-key \
  -v jf_manager_data:/data \
  -p 8000:8000 \
  ghcr.io/jugendfeuerwehr-manager/jf-manager-server:latest
```

Nach dem Start ist die Anwendung unter http://localhost:8000 erreichbar. 
Beim ersten Zugriff wirst du automatisch zur Einrichtungsseite weitergeleitet, 
wo du einen Administrator-Account erstellen musst.

3. Admin-Benutzer über die Shell erstellen:
```bash
docker exec -it CONTAINER_ID python manage.py migrate
docker exec -it CONTAINER_ID python manage.py createsuperuser
```

Der Admin-Bereich ist unter http://localhost:8000/admin verfügbar.

> **Hinweis**: Für Produktivumgebungen empfehlen wir MySQL/MariaDB oder PostgreSQL:
```bash
# MySQL Beispiel:
docker run -d \
  -e DATABASE_URL=mysql://user:password@host:3306/db \
  -e SECRET_KEY=your-secret-key \
  -p 8000:8000 \
  ghcr.io/jugendfeuerwehr-manager/jf-manager-server:latest
```

### Umgebungsvariablen

- `DATABASE_URL`: Datenbank-Verbindungsstring
- `SECRET_KEY`: Django Secret Key
- `DEBUG`: Debug-Modus (True/False)
- `ALLOWED_HOSTS`: Erlaubte Hostnamen (kommagetrennt)
- `DJANGO_SUPERUSER_USERNAME`: Admin Benutzername (optional)
- `DJANGO_SUPERUSER_PASSWORD`: Admin Passwort (optional)
- `DJANGO_SUPERUSER_EMAIL`: Admin E-Mail (optional)



## 📚 Dokumentation

Aktuell in Arbeit.

## 📦 Drittanbieter-Software

JF-Manager verwendet die folgende Drittanbieter-Software:

| Projekt       | Beschreibung                                                | Lizenz                                                                 |
|---------------|--------------------------------------------------------------|------------------------------------------------------------------------|
| Metis Menu    | Ein einfaches, leichtgewichtiges Menü-Plugin für Bootstrap.  | [MIT License](https://opensource.org/licenses/MIT)                     |
| QuaggaJS      | Eine Barcode-Scanner-Bibliothek, die auf JavaScript und HTML5 basiert. | [MIT License](https://opensource.org/licenses/MIT)                     |
| Raphael       | Eine JavaScript-Bibliothek zum Zeichnen von Vektorgrafiken.  | [MIT License](https://opensource.org/licenses/MIT)                     |
| Font Awesome  | Eine beliebte Icon-Bibliothek, die skalierbare Vektorsymbole bietet. | [Font Awesome Free License](https://fontawesome.com/license/free)      |

## 🤝 Beitragen

Wir freuen uns über Beiträge zur Verbesserung des JF-Managers! Bitte lies dir unsere Beitragsrichtlinien durch, bevor du Änderungen vorschlägst.

## 📄 Lizenz

[GNU AFFERO GENERAL PUBLIC LICENSE](./LICENSE)


## 🚧 Roadmap

- Funktion der Kleiderkammer vereinfachen und die Lagerhaltung nach Lagerstetten umstellen
- Responsive Design stellenweise Fehlerhaft. Das optimieren.
- Altlasten Entfernen
- E-Mail Funktion integrieren.
- usw.
