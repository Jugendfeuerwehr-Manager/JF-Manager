const models: Record<string, string> = {
  'members.member': 'Mitglieder', 'members.parent': 'Elternkontakte', 'members.group': 'Gruppen',
  'members.memberlist': 'Listen', 'members.memberlistentry': 'Listeneinträge', 'members.emailmessage': 'Nachrichten',
  'servicebook.service': 'Dienste', 'servicebook.attendance': 'Anwesenheiten',
  'training.trainingsession': 'Übungen', 'training.trainingblock': 'Übungsbausteine',
  'training.libraryblock': 'Bibliotheksbausteine', 'training.libraryblockcategory': 'Bibliothekskategorien', 'training.libraryblocktag': 'Schlagwörter',
  'qualifications.qualification': 'Qualifikationen', 'qualifications.specialtask': 'Sonderaufgaben',
  'qualifications.qualificationtype': 'Qualifikationstypen', 'qualifications.specialtasktype': 'Aufgabentypen',
  'inventory.item': 'Artikel', 'inventory.itemvariant': 'Artikelvarianten', 'inventory.storagelocation': 'Lagerorte',
  'inventory.category': 'Inventarkategorien',
  'inventory.stock': 'Bestände', 'inventory.transaction': 'Bestandsbewegungen',
  'orders.order': 'Bestellungen', 'orders.orderitem': 'Bestellpositionen', 'orders.orderableitem': 'Bestellkatalog',
  'users.customuser': 'Konten', 'auth.group': 'Berechtigungsgruppen', 'departments.department': 'Abteilungen',
  'departments.userdepartmentrole': 'Abteilungszuordnungen', 'departments.roletemplate': 'Rollenvorlagen',
}
const special: Record<string, string> = {
  '*': 'Alle Rechte des Notfallkontos',
  'departments.can_access_all_departments': 'Datenbereich der gesamten Organisation',
  'departments.can_manage_all_departments': 'Abteilungen verwalten',
  'departments.can_assign_roles': 'Rollen administrativ zuweisen',
  'departments.can_delegate_roles': 'Freigegebene Abteilungsrollen zuweisen',
  'departments.can_delegate_department_leadership': 'Abteilungsleitungen zuweisen',
  'training.can_manage_training': 'Übungen und Pläne bearbeiten',
  'training.can_manage_library': 'Gemeinsame Bibliothek pflegen',
  'inventory.can_rent': 'Material ausgeben und zurücknehmen',
  'orders.can_manage_orders': 'Bestellungen verwalten', 'orders.can_change_order_status': 'Bestellstatus ändern',
  'orders.can_receive_order': 'Bestell-Wareneingänge buchen',
  'members.can_send_member_emails': 'Nachrichten an Mitglieder versenden',
  'settings_manager.view_all_settings': 'Anwendungseinstellungen ansehen',
  'settings_manager.change_all_settings': 'Anwendungseinstellungen ändern',
}
export function permissionLabel(name: string): string {
  if (special[name]) return special[name]
  const [app, code = ''] = name.split('.')
  const match = /^(view|add|change|delete|export)_(.+)$/.exec(code)
  if (match) {
    const label = models[`${app}.${match[2]}`]
    const verb = { view: 'ansehen', add: 'anlegen', change: 'bearbeiten', delete: 'löschen', export: 'exportieren' }[match[1] as 'view']
    if (label) return `${label} ${verb}`
  }
  return 'Weitere Berechtigung (siehe erweiterte Ansicht)'
}
