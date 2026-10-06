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
  'members.attachment': 'Mitgliederanhänge', 'members.emailattachment': 'Nachrichtenanhänge', 'members.emailrecipient': 'Nachrichtenempfänger',
  'members.event': 'Mitgliederereignisse', 'members.eventtype': 'Ereignisarten', 'members.status': 'Mitgliedsstatus', 'members.exportaudit': 'Exportnachweise',
  'servicebook.staffattendance': 'Betreueranwesenheiten',
  'training.trainingblockmaterial': 'Übungsmaterial', 'training.trainingmedia': 'Übungsanhänge', 'training.trainingtemplate': 'Übungsvorlagen', 'training.trainingtemplateblock': 'Vorlagenbausteine',
  'orders.orderstatus': 'Bestellstatus', 'orders.orderitemstatushistory': 'Bestellstatusverlauf', 'orders.emailtemplate': 'Bestell-E-Mail-Vorlagen', 'orders.emaillayouttemplate': 'E-Mail-Layouts',
  'orders.notificationpreference': 'Bestellbenachrichtigungen', 'orders.notificationlog': 'Benachrichtigungsverlauf',
  'settings_manager.ldapconfig': 'LDAP-Anbindung', 'settings_manager.ldapdepartmentrolemapping': 'LDAP-Rollenzuordnung',
  'settings_manager.oidcconfig': 'OIDC-Anmeldung', 'settings_manager.oidcgroupmapping': 'OIDC-Rollenzuordnung', 'settings_manager.settingscategory': 'Einstellungskategorien',
  'external_sync.syncjob': 'Datenabgleich', 'external_sync.syncbinding': 'Abgleich-Zuordnungen', 'external_sync.syncrun': 'Abgleichverlauf',
  'auth.permission': 'Einzelne Berechtigungen', 'users.usersession': 'Anmeldesitzungen',
  'notifications.pushsubscription': 'Push-Anmeldungen', 'notifications.pushdelivery': 'Push-Zustellungen',
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
  'inventory.clear_former_member_names': 'Namen ehemaliger Mitglieder anonymisieren',
  'external_sync.run_syncjob': 'Datenabgleich ausführen', 'external_sync.test_syncjob': 'Abgleichverbindung prüfen', 'external_sync.garbage_collect_syncjob': 'Abgleichdaten bereinigen',
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
  if (app === 'settings_manager') {
    const setting = /^(view|change)_(email|general|ldap|member|oidc|order|service)_settings$/.exec(code)
    if (setting) {
      const area: Record<string, string> = { email: 'E-Mail-Einstellungen', general: 'Allgemeine Einstellungen', ldap: 'LDAP-Einstellungen', member: 'Mitgliedereinstellungen', oidc: 'OIDC-Einstellungen', order: 'Bestelleinstellungen', service: 'Dienstbucheinstellungen' }
      return `${area[setting[2]!]} ${setting[1] === 'view' ? 'ansehen' : 'ändern'}`
    }
  }
  const match = /^(view|add|change|delete|export)_(.+)$/.exec(code)
  if (match) {
    const label = models[`${app}.${match[2]}`]
    const verb = { view: 'ansehen', add: 'anlegen', change: 'bearbeiten', delete: 'löschen', export: 'exportieren' }[match[1] as 'view']
    if (label) return `${label} ${verb}`
  }
  return 'Weitere Berechtigung (siehe erweiterte Ansicht)'
}
