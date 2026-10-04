# ROLE-01.1: Rollen- und Permission-Vertrag

Stand: 04.10.2026. Dieses Manifest ist die fachliche Eingabe für die spätere Vorlagenanlage. Es vergibt selbst keine Rechte. Die technischen Permission-Namen wurden gegen die aktuell geladenen Django-Modelle geprüft.

## Geltung und Metadaten

Jede Vorlage erhält einen unveränderlichen Schlüssel, Anzeigenamen, Beschreibung, Versionsnummer, erlaubte Bereiche (`organization`, `department`) und eine anfänglich gesetzte Delegierbarkeit. Die Permissions bleiben ausschließlich in Django-Gruppen. Eine Abteilungszuweisung nutzt `UserDepartmentRole.groups`; eine Organisationszuweisung nutzt die globale Benutzer-Gruppenzuordnung. `departments.can_access_all_departments` erweitert den Datenbereich, ersetzt aber kein Fachrecht. Keine Vorlage verleiht allein wegen `is_staff` fachliche Rechte.

| Schlüssel | Anzeigename | Bereich | Anfangs delegierbar | Permission-Bausteine |
| --- | --- | --- | --- | --- |
| `youth_director` | Jugendwart | Organisation | nein | `member_editor`, `parent_editor`, `group_editor`, `list_editor`, `list_exporter`, `service_editor`, `training_editor`, `qualification_editor`, `task_editor`, `organization_scope` |
| `department_youth_director` | Abteilungsjugendwart | Abteilung | nein | Dieselben Fachbausteine ohne `organization_scope` |
| `youth_leader` | Jugendleiter | Abteilung | ja, nach Freigabe | `member_reader`, `parent_reader`, `group_reader`, `list_editor`, `service_editor`, `training_editor`, `qualification_reader` |
| `supervisor` | Betreuer | Abteilung | ja, nach Freigabe | `member_reader`, `parent_reader`, `service_reader`, `attendance_editor`, `training_reader` |
| `inventory_manager`, `inventory_manager_organization` | Inventarverwaltung | Abteilung / Organisation | ja, nach Freigabe | `inventory_editor`; Organisationsvariante zusätzlich `organization_scope` |
| `order_manager`, `order_manager_organization` | Bestellverwaltung | Abteilung / Organisation | ja, nach Freigabe | `order_editor`, `inventory_reader`; Organisationsvariante zusätzlich `organization_scope` |
| `email_communicator`, `email_communicator_organization` | E-Mail-Kommunikation | Abteilung / Organisation | ja, nach Freigabe | `member_reader`, `email_sender`; Organisationsvariante zusätzlich `organization_scope` |
| `training_planner`, `training_planner_organization` | Ausbildungsplanung | Abteilung / Organisation | ja, nach Freigabe | `training_editor`, `group_reader`; Organisationsvariante zusätzlich `organization_scope` |
| `library_editor` | Bibliotheksredaktion | Organisation | nein | `library_editor`, `organization_scope` |
| `qualification_manager`, `qualification_manager_organization` | Qualifikationsverwaltung | Abteilung / Organisation | ja, nach Freigabe | `qualification_editor`, `task_editor`, `member_reader`; Organisationsvariante zusätzlich `organization_scope` |
| `system_administrator` | Systemadministration | Organisation | nein | `identity_admin`, `department_admin`, `organization_scope`; `settings_admin` wartet auf CFG-01, keine fachlichen Lese- oder Schreibbausteine |

Die elf fachlichen Rollentypen ergeben sechzehn technische Vorlagen: Bei Inventar, Bestellung, E-Mail, Ausbildungsplanung und Qualifikationen benötigen Abteilung und Organisation wegen ihrer unterschiedlichen Bereichsberechtigung getrennte Gruppen und stabile Schlüssel. Der Schlüssel ohne Suffix bezeichnet die Abteilungsvariante. Alle Vorlagen beginnen mit Version 1. „Delegierbar“ bedeutet nur Vorlagenfähigkeit; die Freigabe und tatsächliche Zuweisung gehören zu ROLE-02. Insbesondere Leitungspersonen erhalten keine Inventar-, Bestell- oder Versandberechtigung automatisch. Die endgültige Permission-Menge und Version jeder Vorlage stehen in `backend/departments/role_catalog.py`; die folgenden Bausteine erklären diesen Vertrag lesbar. Der Seed vergleicht bestehende Vorlagen und Gruppen vor jeder Anlage und ändert sie bei Abweichung nicht.

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
| `list_exporter` | `members.export_memberlist`; ausschließlich Jugendwart und Abteilungsjugendwart, nicht Jugendleiter oder Betreuer |
| `service_reader` | `servicebook.view_service`, `servicebook.view_attendance` |
| `attendance_editor` | `servicebook.view_attendance`, `servicebook.add_attendance`, `servicebook.change_attendance` |
| `service_editor` | `servicebook.view_service`, `servicebook.add_service`, `servicebook.change_service`, `servicebook.view_attendance`, `servicebook.add_attendance`, `servicebook.change_attendance` |
| `training_reader` | `training.view_trainingsession`, `training.view_trainingblock` |
| `training_editor` | `training.view_trainingsession`, `training.add_trainingsession`, `training.change_trainingsession`, `training.view_trainingblock`, `training.add_trainingblock`, `training.change_trainingblock`, `training.can_manage_training` |
| `library_editor` | `training.view_libraryblock`, `training.add_libraryblock`, `training.change_libraryblock`, `training.view_libraryblockcategory`, `training.add_libraryblockcategory`, `training.change_libraryblockcategory`, `training.view_libraryblocktag`, `training.add_libraryblocktag`, `training.change_libraryblocktag`, `training.can_manage_library` |
| `qualification_reader` | `qualifications.view_qualification`, `qualifications.view_specialtask` |
| `qualification_editor` | `qualifications.view_qualification`, `qualifications.add_qualification`, `qualifications.change_qualification`, `qualifications.view_qualificationtype` |
| `task_editor` | `qualifications.view_specialtask`, `qualifications.add_specialtask`, `qualifications.change_specialtask`, `qualifications.view_specialtasktype` |
| `inventory_reader` | `inventory.view_item`, `inventory.view_itemvariant`, `inventory.view_storagelocation`, `inventory.view_stock` |
| `inventory_editor` | `inventory.view_item`, `inventory.add_item`, `inventory.change_item`, `inventory.view_itemvariant`, `inventory.add_itemvariant`, `inventory.change_itemvariant`, `inventory.view_storagelocation`, `inventory.add_storagelocation`, `inventory.change_storagelocation`, `inventory.view_stock`, `inventory.add_stock`, `inventory.view_transaction`, `inventory.add_transaction`, `inventory.can_rent` |
| `order_editor` | `orders.view_order`, `orders.add_order`, `orders.change_order`, `orders.can_manage_orders`, `orders.can_change_order_status`, `orders.view_orderitem`, `orders.add_orderitem`, `orders.change_orderitem`, `orders.view_orderableitem` |
| `email_sender` | `members.can_send_member_emails`, `members.view_emailmessage`, `members.add_emailmessage` |
| `identity_admin` | `users.view_customuser`, `users.add_customuser`, `users.change_customuser`, `auth.view_group`, `auth.add_group`, `auth.change_group`, `departments.view_userdepartmentrole`, `departments.add_userdepartmentrole`, `departments.change_userdepartmentrole`, `departments.view_roletemplate`, `departments.add_roletemplate`, `departments.change_roletemplate` |
| `department_admin` | `departments.view_department`, `departments.add_department`, `departments.change_department`, `departments.can_manage_all_departments` |
| `settings_admin` | Noch kein einheitlicher Permission-Vertrag; CFG-01 legt die Felder und Rechte fest. |

## Offene Grenzen vor Aktivierung

1. ROLE-01.2 hat `training.can_manage_training` und `training.can_manage_library` ausgeliefert. Die Trainings-API prüft das Trainingsrecht noch global über `user.has_perm`; vor der Aktivierung abteilungsgebundener `training_editor`-Vorlagen ist ihre Bereichsprüfung mit SEC-01/02 abzugleichen.
2. `members.export_memberlist` ist ein gesondertes Recht und gehört nur zu beiden fachlichen Leitungsrollen. Weitere fachliche Export-, Rollenzuweisungs-, Anonymisierungs- und Einstellungsrechte sind noch nicht durchgängig als separate Permissions und Endpunktprüfungen vorhanden. Sie werden keiner Standardvorlage stillschweigend als Ersatz über `view`, `change` oder `delete` zugeschlagen. ROLE-02 und CFG-01 benötigen dafür explizite Verträge.
3. `orders.can_manage_orders` und die Trainings-Sonderrechte werden aktuell von Teilen der API global über `user.has_perm` geprüft. Eine abteilungsgebundene Fachrolle darf erst nach SEC-01/02-Abnahme und gegebenenfalls bereichsbezogener API-Anpassung aktiviert werden. Das gilt entsprechend für zentrale Inventarobjekte: Organisationssicht plus globales Fachrecht ist erforderlich.
4. Der irreführende Staff-Bypass-Docstring in `UserDepartmentRole` wurde in ROLE-01.3 korrigiert. Die tatsächlichen Endpunkte und Tests bleiben der Berechtigungsnachweis.
5. Der Seed erkennt vorhandene Django-Gruppen nicht anhand eines gleichen Anzeigenamens als Vorlage und verändert gebundene Gruppen bei Abweichungen nicht. ROLE-01.5 muss bestehende Gruppen, Rechte und Zuweisungen für eine explizite Zuordnung sichtbar machen.
6. `settings_admin` ist fachlich noch nicht definiert. Die technische Vorlage `system_administrator` enthält nur die bereits ausgelieferten Identitäts-, Gruppen- und Abteilungsrechte; CFG-01 muss den Einstellungsteil vor produktiver Zuweisung ergänzen. Der Seed weist keine Vorlage einem Benutzer zu.

## ROLE-01.5: bestehende Gruppen ausdrücklich zuordnen

`reconcile_role_groups` zeigt ohne Parameter vorhandene Django-Gruppen mit Permission-Namen, direkten Benutzer-IDs, Abteilungszuordnungen und LDAP-/OIDC-Mapping-IDs. Mit `--template-key SCHLÜSSEL --group-id ID` zeigt der Command den Soll/Ist-Rechtevergleich, die bisherige Vorlagengruppe samt Zuweisungen und einen Fingerprint. Erst ein erneuter Aufruf mit denselben Angaben sowie `--apply --expected FINGERPRINT` bindet genau diese Gruppe. Der Fingerprint verhindert eine Zuordnung auf Basis eines inzwischen veränderten Zustands. Der Command ändert keine Permissions, Gruppenmitgliedschaften, Staff-Flags oder externen Mappings.

Fehlt die Zielvorlage noch, kann der bestätigte Vergleich sie mit dem festen Katalogschlüssel und der ausdrücklich gewählten Altgruppe anlegen. Das deckt einen Gruppennamenskonflikt ab, bei dem der Erstinstallations-Seed sicher abgebrochen hat. Auch dann werden Rechte und Zuweisungen der Altgruppe nicht verändert.

Eine bereits belegte Vorlagengruppe wird nicht ersetzt. Abteilungsvorlagen akzeptieren keine global zugewiesenen Gruppen oder Organisationsberechtigung; Organisationsvorlagen akzeptieren keine Abteilungs- oder externen Rollenabbildungen ohne gesonderte Klärung. Zusätzliche fachliche Rechte einer Altgruppe werden im Vergleich ausdrücklich angezeigt und bei bestätigter Zuordnung erhalten. Der Betreiber muss diese Abweichung vor der Bindung prüfen. Der Command übernimmt keine Gruppe allein wegen ihres Namens und legt bei der Zuordnung keine neue Berechtigung an.
