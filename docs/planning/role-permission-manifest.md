# ROLE-01.1: Rollen- und Permission-Vertrag

Stand: 04.10.2026. Dieses Manifest ist die fachliche Eingabe für die spätere Vorlagenanlage. Es vergibt selbst keine Rechte. Die technischen Permission-Namen wurden gegen die aktuell geladenen Django-Modelle geprüft.

## Geltung und Metadaten

Jede Vorlage erhält einen unveränderlichen Schlüssel, Anzeigenamen, Beschreibung, Versionsnummer, erlaubte Bereiche (`organization`, `department`) und eine anfänglich gesetzte Delegierbarkeit. Die Permissions bleiben ausschließlich in Django-Gruppen. Eine Abteilungszuweisung nutzt `UserDepartmentRole.groups`; eine Organisationszuweisung nutzt die globale Benutzer-Gruppenzuordnung. `departments.can_access_all_departments` erweitert den Datenbereich, ersetzt aber kein Fachrecht. Keine Vorlage verleiht allein wegen `is_staff` fachliche Rechte.

| Schlüssel | Anzeigename | Bereich | Anfangs delegierbar | Permission-Bausteine |
| --- | --- | --- | --- | --- |
| `youth_director` | Jugendwart | Organisation | nein | `member_editor`, `parent_editor`, `group_editor`, `list_editor`, `service_editor`, `training_editor`, `qualification_editor`, `task_editor`, `organization_scope` |
| `department_youth_director` | Abteilungsjugendwart | Abteilung | nein | Dieselben Fachbausteine ohne `organization_scope` |
| `youth_leader` | Jugendleiter | Abteilung | ja, nach Freigabe | `member_reader`, `parent_reader`, `group_reader`, `list_editor`, `service_editor`, `training_editor`, `qualification_reader` |
| `supervisor` | Betreuer | Abteilung | ja, nach Freigabe | `member_reader`, `parent_reader`, `service_reader`, `attendance_editor`, `training_reader` |
| `inventory_manager` | Inventarverwaltung | Abteilung oder Organisation | ja, nach Freigabe | `inventory_editor`; Organisationsvariante zusätzlich `organization_scope` |
| `order_manager` | Bestellverwaltung | Abteilung oder Organisation | ja, nach Freigabe | `order_editor`, `inventory_reader`; Organisationsvariante zusätzlich `organization_scope` |
| `email_communicator` | E-Mail-Kommunikation | Abteilung oder Organisation | ja, nach Freigabe | `member_reader`, `email_sender`; Organisationsvariante zusätzlich `organization_scope` |
| `training_planner` | Ausbildungsplanung | Abteilung oder Organisation | ja, nach Freigabe | `training_editor`, `group_reader`; Organisationsvariante zusätzlich `organization_scope` |
| `library_editor` | Bibliotheksredaktion | Organisation | nein | `library_editor`, `organization_scope` |
| `qualification_manager` | Qualifikationsverwaltung | Abteilung oder Organisation | ja, nach Freigabe | `qualification_editor`, `task_editor`, `member_reader`; Organisationsvariante zusätzlich `organization_scope` |
| `system_administrator` | Systemadministration | Organisation | nein | `identity_admin`, `settings_admin`, `department_admin`, `organization_scope`; keine fachlichen Lese- oder Schreibbausteine |

Alle Vorlagen beginnen mit Version 1. „Delegierbar“ bedeutet nur Vorlagenfähigkeit; die Freigabe und tatsächliche Zuweisung gehören zu ROLE-02. Insbesondere Leitungspersonen erhalten keine Inventar-, Bestell- oder Versandberechtigung automatisch. Die endgültige Permission-Menge einer Vorlage wird vor dem Seed als explizite, versionierte Liste festgehalten; Bausteine sind nur eine lesbare Darstellung dieses Vertrags.

## Vorhandene Permission-Bausteine

Die folgenden Namen existieren als Django-Modellpermissions. `view`/`add`/`change` stehen für getrennte Berechtigungen; `delete` gehört zu keiner Standardvorlage. Bei gemeinsamen Stammdaten und verschachtelten Beziehungen bleibt die tatsächliche Objektabteilung maßgeblich.

| Baustein | Derzeit vorhandene Permissions |
| --- | --- |
| `organization_scope` | `departments.can_access_all_departments` |
| `member_reader` | `members.view_member` |
| `member_editor` | `members.view_member`, `members.add_member`, `members.change_member` |
| `parent_reader` | `members.view_parent` |
| `parent_editor` | `members.view_parent`, `members.add_parent`, `members.change_parent` |
| `group_reader` | `members.view_group` |
| `group_editor` | `members.view_group`, `members.add_group`, `members.change_group` |
| `list_editor` | `members.view_memberlist`, `members.add_memberlist`, `members.change_memberlist`, `members.view_memberlistentry`, `members.add_memberlistentry`, `members.change_memberlistentry` |
| `service_reader` | `servicebook.view_service`, `servicebook.view_attendance` |
| `attendance_editor` | `servicebook.view_attendance`, `servicebook.add_attendance`, `servicebook.change_attendance` |
| `service_editor` | `servicebook.view_service`, `servicebook.add_service`, `servicebook.change_service`, `servicebook.view_attendance`, `servicebook.add_attendance`, `servicebook.change_attendance` |
| `training_reader` | `training.view_trainingsession`, `training.view_trainingblock` |
| `training_editor` | `training.view_trainingsession`, `training.add_trainingsession`, `training.change_trainingsession`, `training.view_trainingblock`, `training.add_trainingblock`, `training.change_trainingblock` |
| `library_editor` | `training.view_libraryblock`, `training.add_libraryblock`, `training.change_libraryblock`, `training.view_libraryblockcategory`, `training.add_libraryblockcategory`, `training.change_libraryblockcategory`, `training.view_libraryblocktag`, `training.add_libraryblocktag`, `training.change_libraryblocktag` |
| `qualification_reader` | `qualifications.view_qualification`, `qualifications.view_specialtask` |
| `qualification_editor` | `qualifications.view_qualification`, `qualifications.add_qualification`, `qualifications.change_qualification`, `qualifications.view_qualificationtype` |
| `task_editor` | `qualifications.view_specialtask`, `qualifications.add_specialtask`, `qualifications.change_specialtask`, `qualifications.view_specialtasktype` |
| `inventory_reader` | `inventory.view_item`, `inventory.view_itemvariant`, `inventory.view_storagelocation`, `inventory.view_stock` |
| `inventory_editor` | `inventory.view_item`, `inventory.add_item`, `inventory.change_item`, `inventory.view_itemvariant`, `inventory.add_itemvariant`, `inventory.change_itemvariant`, `inventory.view_storagelocation`, `inventory.add_storagelocation`, `inventory.change_storagelocation`, `inventory.view_stock`, `inventory.add_stock`, `inventory.view_transaction`, `inventory.add_transaction`, `inventory.can_rent` |
| `order_editor` | `orders.view_order`, `orders.add_order`, `orders.change_order`, `orders.can_manage_orders`, `orders.can_change_order_status`, `orders.view_orderitem`, `orders.add_orderitem`, `orders.change_orderitem`, `orders.view_orderableitem` |
| `email_sender` | `members.can_send_member_emails`, `members.view_emailmessage`, `members.add_emailmessage` |
| `identity_admin` | `users.view_customuser`, `users.add_customuser`, `users.change_customuser`, `auth.view_group`, `auth.add_group`, `auth.change_group`, `departments.view_userdepartmentrole`, `departments.add_userdepartmentrole`, `departments.change_userdepartmentrole` |
| `department_admin` | `departments.view_department`, `departments.add_department`, `departments.change_department`, `departments.can_manage_all_departments` |
| `settings_admin` | Noch kein einheitlicher Permission-Vertrag; CFG-01 legt die Felder und Rechte fest. |

## Lücken vor Seed und Aktivierung

1. Die Trainings-API verlangt bei Schreibaktionen `training.can_manage_training` beziehungsweise `training.can_manage_library`. Beide Permissions fehlen in den aktuellen Modell-Definitionen. ROLE-01.2 muss sie definieren und die API auf den beabsichtigten Organisations-/Abteilungsbereich prüfen, bevor `training_editor` oder `library_editor` wirksam vergeben werden.
2. Fachliche Export-, Rollenzuweisungs-, Anonymisierungs- und Einstellungsrechte sind noch nicht durchgängig als separate Permissions und Endpunktprüfungen vorhanden. Sie werden keiner Standardvorlage stillschweigend als Ersatz über `view`, `change` oder `delete` zugeschlagen. ROLE-01.2 und ROLE-02 benötigen dafür explizite Verträge; CFG-01 definiert Einstellungen.
3. `orders.can_manage_orders` und die Trainings-Sonderrechte werden aktuell von Teilen der API global über `user.has_perm` geprüft. Eine abteilungsgebundene Fachrolle darf erst nach SEC-01/02-Abnahme und gegebenenfalls bereichsbezogener API-Anpassung aktiviert werden. Das gilt entsprechend für zentrale Inventarobjekte: Organisationssicht plus globales Fachrecht ist erforderlich.
4. `UserDepartmentRole` beschreibt im Docstring noch einen Staff-Bypass, der dem verbindlichen Rollenvertrag widerspricht. Der Docstring ist kein Berechtigungsnachweis; die tatsächlichen Endpunkte und Tests entscheiden. Eine Korrektur folgt mit der Rollenmodell-Implementierung.
5. Vorhandene Django-Gruppen werden beim Seed nicht anhand des Anzeigenamens als Vorlage erkannt. Die spätere Migration muss bestehende Rechte und Zuweisungen anzeigen und eine explizite Zuordnung verlangen. Kundenseitig geänderte Vorlagengruppen dürfen bei Updates nicht überschrieben werden.
