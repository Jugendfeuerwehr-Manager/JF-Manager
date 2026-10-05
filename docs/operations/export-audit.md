# Tabellenexporte und Audit

Mitglieder-XLSX verlangt `members.view_member` und `members.export_member` im selben zulässigen Bereich. Listen-XLSX verlangt weiterhin `members.view_memberlist` und `members.export_memberlist`. Elternspalten erfordern zusätzlich sichtbare Elternkontakte. Die Leitungsvorlagen Version 2 bieten das neue Mitgliederexportrecht zur ausdrücklichen Übernahme an; bestehende Gruppen werden nicht automatisch erweitert.

Zeichenfolgen werden als Textzellen geschrieben, Datums- und Zahlenwerte bleiben typisiert. Führende Nullen bleiben erhalten. Excel-unzulässige Steuerzeichen werden entfernt. Formeln aus Benutzereingaben werden nicht ausgeführt.

Die Tabelle `members_exportaudit` protokolliert XLSX-Aufrufe einschließlich abgewiesener Aufrufe: Akteur-ID, Aktion, Objekttyp/-ID, Abteilungs-IDs, Zeit und HTTP-Ergebnis. Keine Exportinhalte, Suchfilter, Namen oder Dateinamen. Antworten sind `private, no-store`.

`AUDIT_RETENTION_DAYS` legt die Aufbewahrung fest (Standard 180 Tage). `python manage.py purge_export_audits` täglich im Betriebsplan ausführen. Der Befehl löscht ausschließlich abgelaufene Exportmetadaten. Für Backups gilt zusätzlich deren festgelegte Aufbewahrung. Lokales Drucken bereits sichtbarer Daten erzeugt keinen serverseitigen Exportaufruf und damit keinen solchen Auditeintrag.
