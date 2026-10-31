# Betroffenenanfragen

Anfragen dokumentieren (Eingang, Identitätsprüfung, Antwort) und innerhalb eines Monats beantworten (Art. 12 Abs. 3). Bei Minderjährigen handeln in der Regel die Sorgeberechtigten.

| Recht | So geht es in JF-Manager | Recht in der Anwendung |
| --- | --- | --- |
| Auskunft / Datenübertragbarkeit (Art. 15, 20) | Mitglied, Elternteil oder Konto öffnen → **Einwilligungen → Datenauskunft**. Lädt ein ZIP mit `daten.json` und Dateien; erneute Bestätigung nötig, wird protokolliert. | `members.export_member` bzw. Benutzerverwaltung |
| Berichtigung (Art. 16) | Datensatz bearbeiten; Eltern können Änderungen auch über das Portal beantragen. | `members.change_member` / `change_parent` |
| Löschung (Art. 17) | **Anonymisieren** (behält Statistik) oder **Löschen** (vollständig) im Mitgliederprofil. Vorher die Person in Spond/Hi-Org entfernen, sonst legt der Abgleich sie neu an. | `members.anonymize_member` bzw. `delete_member` |
| Einschränkung (Art. 18) | Austrittsdatum setzen und Datensatz nicht weiter nutzen; Portalzugang beenden. | `members.change_member` |
| Widerspruch / Widerruf (Art. 21, Art. 7 Abs. 3) | Unter **Einwilligungen** „Widerrufen“ erfassen; z. B. Foto-Einwilligung. Der Verlauf bleibt als Nachweis. | `members.change_member` |

Gelöschte Daten bleiben in Sicherungen bis zu deren Ablauf erhalten (bis etwa sechs Monate). Bei einer Wiederherstellung führt der nächste nächtliche Lauf die Fristen erneut aus.
