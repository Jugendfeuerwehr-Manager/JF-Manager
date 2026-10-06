# ROLE-01.1: Rollen- und Permission-Vertrag

Stand: 06.10.2026. Dieses Manifest beschreibt die ausgelieferten Vorlagen und ihren Rechtevertrag. Es vergibt selbst keine Rechte. Die technischen Permission-Namen wurden gegen die aktuell geladenen Django-Modelle geprüft.

## Geltung und Metadaten

Jede Vorlage erhält einen unveränderlichen Schlüssel, Anzeigenamen, Beschreibung, Versionsnummer, erlaubte Bereiche (`organization`, `department`) und eine anfänglich gesetzte Delegierbarkeit. Die Permissions bleiben ausschließlich in Django-Gruppen. Eine Abteilungszuweisung nutzt `UserDepartmentRole.groups`; eine Organisationszuweisung nutzt die globale Benutzer-Gruppenzuordnung. `departments.can_access_all_departments` erweitert den Datenbereich, ersetzt aber kein Fachrecht. Keine Vorlage verleiht allein wegen `is_staff` fachliche Rechte.

| Schlüssel | Anzeigename | Bereich | Anfangs delegierbar | Permission-Bausteine |
| --- | --- | --- | --- | --- |
| `youth_director` | Jugendwart | Organisation | nein | `member_editor`, `parent_editor`, `group_editor`, `list_editor`, `list_exporter`, `service_editor`, `training_editor`, `qualification_editor`, `task_editor`, `organization_scope`, `delegation`, `leadership_delegation` |
| `department_youth_director` | Abteilungsjugendwart | Abteilung | nein | Dieselben Fachbausteine ohne `organization_scope` und `leadership_delegation`, mit `delegation` |
| `youth_leader` | Jugendleiter | Abteilung | ja, nach Freigabe | `member_reader`, `parent_reader`, `group_reader`, `list_editor`, `service_editor`, `training_editor`, `qualification_reader` |
| `supervisor` | Betreuer | Abteilung | ja, nach Freigabe | `member_reader`, `parent_reader`, `service_reader`, `attendance_editor`, `training_reader` |
| `inventory_manager`, `inventory_manager_organization` | Inventarverwaltung | Abteilung / Organisation | ja, nach Freigabe | `inventory_editor`; Organisationsvariante zusätzlich `organization_scope` |
| `order_manager`, `order_manager_organization` | Bestellverwaltung | Abteilung / Organisation | ja, nach Freigabe | `order_editor`, `inventory_reader`; Organisationsvariante zusätzlich `organization_scope` |
| `email_communicator`, `email_communicator_organization` | E-Mail-Kommunikation | Abteilung / Organisation | ja, nach Freigabe | `member_reader`, `email_sender`; Organisationsvariante zusätzlich `organization_scope` |
| `training_planner`, `training_planner_organization` | Ausbildungsplanung | Abteilung / Organisation | ja, nach Freigabe | `training_editor`, `group_reader`; Organisationsvariante zusätzlich `organization_scope` |
| `library_editor` | Bibliotheksredaktion | Organisation | nein | `library_editor`, `organization_scope` |
| `qualification_manager`, `qualification_manager_organization` | Qualifikationsverwaltung | Abteilung / Organisation | ja, nach Freigabe | `qualification_editor`, `task_editor`, `member_reader`; Organisationsvariante zusätzlich `organization_scope` |
| `system_administrator` | Systemadministration | Organisation | nein | `identity_admin`, `department_admin`, `organization_scope`; `settings_admin`, keine fachlichen Lese- oder Schreibbausteine |

Die elf fachlichen Rollentypen ergeben sechzehn technische Vorlagen: Bei Inventar, Bestellung, E-Mail, Ausbildungsplanung und Qualifikationen benötigen Abteilung und Organisation wegen ihrer unterschiedlichen Bereichsberechtigung getrennte Gruppen und stabile Schlüssel. Der Schlüssel ohne Suffix bezeichnet die Abteilungsvariante. Jugendwart und Abteilungsjugendwart stehen auf Version 3; Inventar-/Bestellvarianten und Systemadministration auf Version 2; übrige Vorlagen auf Version 1. „Delegierbar“ bezeichnet die Vorlagenfähigkeit: Abteilungsrollen benötigen zusätzlich eine administrative Freigabe ihrer aktuellen Permission-Menge. Organisationsrollen vergibt nur die Systemadministration. Insbesondere Leitungspersonen erhalten keine Inventar-, Bestell- oder Versandberechtigung automatisch. Die endgültige Permission-Menge und Version jeder Vorlage stehen in `backend/departments/role_catalog.py`; die folgenden Bausteine erklären diesen Vertrag lesbar. Der Seed vergleicht bestehende Vorlagen und Gruppen vor jeder Anlage und ändert sie bei Abweichung nicht.

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
| `list_exporter` | `members.export_memberlist`, `members.export_member`; ausschließlich Jugendwart und Abteilungsjugendwart, nicht Jugendleiter oder Betreuer |
| `service_reader` | `servicebook.view_service`, `servicebook.view_attendance` |
| `attendance_editor` | `servicebook.view_attendance`, `servicebook.add_attendance`, `servicebook.change_attendance` |
| `service_editor` | `servicebook.view_service`, `servicebook.add_service`, `servicebook.change_service`, `servicebook.view_attendance`, `servicebook.add_attendance`, `servicebook.change_attendance` |
| `training_reader` | `training.view_trainingsession`, `training.view_trainingblock` |
| `training_editor` | `training.view_trainingsession`, `training.add_trainingsession`, `training.change_trainingsession`, `training.view_trainingblock`, `training.add_trainingblock`, `training.change_trainingblock`, `training.can_manage_training` |
| `library_editor` | `training.view_libraryblock`, `training.add_libraryblock`, `training.change_libraryblock`, `training.view_libraryblockcategory`, `training.add_libraryblockcategory`, `training.change_libraryblockcategory`, `training.view_libraryblocktag`, `training.add_libraryblocktag`, `training.change_libraryblocktag`, `training.can_manage_library` |
| `qualification_reader` | `qualifications.view_qualification`, `qualifications.view_specialtask` |
| `qualification_editor` | `qualifications.view_qualification`, `qualifications.add_qualification`, `qualifications.change_qualification`, `qualifications.view_qualificationtype` |
| `task_editor` | `qualifications.view_specialtask`, `qualifications.add_specialtask`, `qualifications.change_specialtask`, `qualifications.view_specialtasktype` |
| `inventory_reader` | `inventory.view_category`, `inventory.view_item`, `inventory.view_itemvariant`, `inventory.view_storagelocation`, `inventory.view_stock` |
| `inventory_editor` | `inventory.view_category`, `inventory.view_item`, `inventory.add_item`, `inventory.change_item`, `inventory.view_itemvariant`, `inventory.add_itemvariant`, `inventory.change_itemvariant`, `inventory.view_storagelocation`, `inventory.add_storagelocation`, `inventory.change_storagelocation`, `inventory.view_stock`, `inventory.add_stock`, `inventory.view_transaction`, `inventory.add_transaction`, `inventory.change_transaction` (Gegenbuchungen), `inventory.can_rent` |
| `order_editor` | `orders.view_order`, `orders.add_order`, `orders.change_order`, `orders.can_manage_orders`, `orders.can_receive_order`, `orders.can_change_order_status`, `orders.view_orderitem`, `orders.add_orderitem`, `orders.change_orderitem`, `orders.view_orderableitem` |
| `email_sender` | `members.can_send_member_emails`, `members.view_emailmessage`, `members.add_emailmessage` |
| `identity_admin` | `departments.can_assign_roles`, `users.view_customuser`, `users.add_customuser`, `users.change_customuser`, `auth.view_group`, `auth.add_group`, `auth.change_group`, `departments.view_userdepartmentrole`, `departments.add_userdepartmentrole`, `departments.change_userdepartmentrole`, `departments.view_roletemplate`, `departments.add_roletemplate`, `departments.change_roletemplate` |
| `department_admin` | `departments.view_department`, `departments.add_department`, `departments.change_department`, `departments.can_manage_all_departments` |
| `settings_admin` | `settings_manager.view_all_settings`, `settings_manager.change_all_settings`; der vollständige Konfigurationsablauf bleibt CFG-01. |
| `delegation` | `departments.can_delegate_roles`; nur im tatsächlichen Abteilungsbereich, nur unverändert freigegebene Abteilungsrollen. |
| `leadership_delegation` | `departments.can_delegate_department_leadership`; Jugendwart darf Abteilungsjugendwarte zuweisen. |

## Bereichs-, Zuweisungs- und Upgradevertrag

- Trainings-/Bestell-Sonderrechte prüfen die tatsächliche Abteilung. Betreuer sehen veröffentlichte Übungen und erhaltene Verlaufseinträge, keine Entwürfe. Organisationssicht erweitert ausschließlich Fachrechte, die global vorliegen; abteilungsgebundene Fachrechte bleiben begrenzt.
- Inventar-/Bestellrollen verwenden eine minimale Personenauswahl (Name, ID und erlaubte Abteilungs-IDs), ohne allgemeines Mitgliederdatenrecht. Zentrale Artikelstammdaten sind fachlich lesbar; zentrale Änderungen verlangen Organisationssicht und globales Fachrecht. Bestell-Wareneingang prüft zusätzlich Artikel und Lagerort und verleiht kein allgemeines Inventarbuchungsrecht.
- Lokale Zuweisung folgt Person → Bereich → Rolle → Wirkung → Speicherung. Selbständerung, privilegierte Ziele für Delegierende und fremde Abteilungen sind gesperrt. Rechteänderungen invalidieren die Delegationsfreigabe. Löschen und Anonymisieren sind initial nicht delegierbar. Administratives Zuweisungsrecht und Leitungsdelegation verlangen MFA; Schreibaktionen verlangen aktuelle Bestätigung.
- Herkunftszeilen (`RoleGrant`) dokumentieren lokal/LDAP/OIDC und werden als Vereinigungsmenge in Django-Gruppen projiziert; sie sind keine zweite Rechteengine. Entzug einer Quelle erhält andere Quellen. Archivierung sperrt neue Zuweisungen, erhält bereits bestehende Rechte.
- Die Datenmigration erhält bestehende unmarkierte Gruppenbindungen konservativ als lokal. Sie errät keine externe Herkunft und erweitert keine Rechte oder Staff-Konten. Alte externe Mappings müssen ausdrücklich an eine passende aktive Vorlage gebunden werden. Rohe LDAP-Gruppenspiegelung ist abgeschaltet, da sie unabhängige lokale Gruppen ersetzen würde.
- Nach `migrate` ergänzt der Seed automatisch fehlende Standardvorlagen und weist niemandem Rollen zu. Versionsabweichungen werden verglichen und in der Rollenverwaltung ausdrücklich übernommen; kundeneigene Berechtigungen bleiben bis zur Bestätigung unverändert. Externe Mappingänderungen verlangen sowohl Konfigurations- als auch Zuweisungsrecht.

Bedienung und Upgrade: [Rollenhandbuch](../domains/roles-and-permissions.md). Tests und Abnahmestand: [Roadmap](security-ux-design-roadmap.md).

## ROLE-01.5: bestehende Gruppen ausdrücklich zuordnen

`reconcile_role_groups` zeigt ohne Parameter vorhandene Django-Gruppen mit Permission-Namen, direkten Benutzer-IDs, Abteilungszuordnungen und LDAP-/OIDC-Mapping-IDs. Mit `--template-key SCHLÜSSEL --group-id ID` zeigt der Command den Soll/Ist-Rechtevergleich, die bisherige Vorlagengruppe samt Zuweisungen und einen Fingerprint. Erst ein erneuter Aufruf mit denselben Angaben sowie `--apply --expected FINGERPRINT` bindet genau diese Gruppe. Der Fingerprint verhindert eine Zuordnung auf Basis eines inzwischen veränderten Zustands. Der Command ändert keine Permissions, Gruppenmitgliedschaften, Staff-Flags oder externen Mappings.

Fehlt die Zielvorlage noch, kann der bestätigte Vergleich sie mit dem festen Katalogschlüssel und der ausdrücklich gewählten Altgruppe anlegen. Das deckt einen Gruppennamenskonflikt ab, bei dem der Erstinstallations-Seed sicher abgebrochen hat. Auch dann werden Rechte und Zuweisungen der Altgruppe nicht verändert.

Eine bereits belegte Vorlagengruppe wird nicht ersetzt. Abteilungsvorlagen akzeptieren keine global zugewiesenen Gruppen oder Organisationsberechtigung; Organisationsvorlagen akzeptieren keine Abteilungs- oder externen Rollenabbildungen ohne gesonderte Klärung. Zusätzliche fachliche Rechte einer Altgruppe werden im Vergleich ausdrücklich angezeigt und bei bestätigter Zuordnung erhalten. Der Betreiber muss diese Abweichung vor der Bindung prüfen. Der Command übernimmt keine Gruppe allein wegen ihres Namens und legt bei der Zuordnung keine neue Berechtigung an.
