# Eltern-/Mitgliederportal und Teilnahmesteuerung: Konzept, Design und Ausführungsplan

Stand: 07.10.2026 · Status: **Konzept abgestimmt, Umsetzung offen** · Mockups: Design-Artifact „Eltern- & Mitgliederportal“ (privat, Freigabe durch den Nutzer): https://claude.ai/artifact/LCgXTvMF4vdoi9ePuHUsKu

Dieses Dokument ist die verbindliche Spezifikation für die Pakete `PORTAL-01` bis `PORTAL-04`, `PART-01` bis `PART-04` und `NOTIF-01`. Ergänzung vom 07.10.2026 (zweite Runde): mobiles Dienstbuch, Benachrichtigungseingang für Verwaltende, anpassbare E-Mail-Vorlagen mit Quick-Action-Links und 1:1-Bindung von Verwaltendenkonten an Mitglieder. Es ergänzt `docs/planning/security-ux-design-roadmap.md` (Abschnitt 6 enthält Paketstatus und Detailblöcke). Arbeitsregeln aus `AGENTS.md` und Roadmap-Abschnitt 5 gelten unverändert: ein Commit je Teilschritt, Fortschritt im selben Commit, ehrliche Prüfergebnisse.

Begriffe: **Dienst** steht für das konfigurierbare Vokabular (Dienst/Training/Übung). **Geplanter Dienst** ist eine veröffentlichte `training.TrainingSession` mit Beginn in der Zukunft. **Dienstbuch** ist `servicebook.Service` und dokumentiert ausschließlich das tatsächlich stattgefundene Ereignis. **Portalkonto** ist ein Benutzerkonto für Eltern oder Mitglieder ohne fachliche Rollen. **Betreuende** sind Konten mit Leitungs-/Fachrollen (Jugendwart, Abteilungsjugendwart, Jugendleiter, Ausbildungsplanung …).

## 1. Ziele und Nicht-Ziele

### 1.1 Ziele

1. Eltern (als Stellvertretung ihrer Kinder) und Mitglieder (ab konfigurierbarer Schwelle) melden sich mit demselben Login-, Passwort-Reset-, MFA- und Sitzungsmechanismus an wie Betreuende.
2. Portalkonten melden sich bzw. die ihnen zugewiesenen Kinder zu **geplanten** Diensten an oder ab.
3. Portalkonten beantragen Änderungen an Namen und Kontaktdaten (eigene und der zugewiesenen Kinder). Betreuende prüfen und übernehmen.
4. Portalkonten sehen nur die von der Verwaltung freigegebenen Datenkategorien.
5. Dienste erhalten Teilnahmevoraussetzungen (Qualifikationen, Geschlecht, Alter, Gruppe, Status, Sonderaufgaben) über einen verständlichen Regel-Konfigurator.
6. Dienste erhalten Höchstteilnehmerzahl, Warteliste, Positionen mit Mindestbesetzung und qualifikationsbezogenen Anforderungen sowie einen Zuteilungsmodus mit Drag-and-drop.
7. Besetzungsregeln werden als Vorlagen gespeichert und wiederverwendet.
8. Das Dienstbuch zeigt Meldestatus (angemeldet, abgemeldet/entschuldigt, Warteliste, zugeteilt, keine Rückmeldung) neben der tatsächlichen Anwesenheit; es wird **mobil zuerst** gestaltet, weil es fast ausschließlich auf dem Smartphone genutzt wird.
9. Verwaltende erhalten einen **Benachrichtigungseingang** für alle externen Ereignisse (Anträge, Meldungen, Besetzung, Konten).
10. Benachrichtigungs-E-Mails sind über das bestehende Mail-Template-System anpassbar und enthalten **Quick-Action-Links**, die nach dem Login wirken.
11. Ein Verwaltendenkonto lässt sich **1:1 an ein Mitglied** binden, damit Verwaltende, die selbst Mitglied sind, kein zweites Konto brauchen.

### 1.2 Nicht-Ziele und harte Grenzen

- Portalkonten sehen **niemals**: Bemerkungen/Notizen (`Member.notes`, `Parent.notes`), Mitgliederereignisse (`members.Event`), Anhänge, Dienstbuchinhalte (Anwesenheit, Abwesenheit, besondere Vorkommnisse, Übungsleitung), Anwesenheitsstatistiken, Namen anderer Teilnehmender, interne Plannotizen, Bausteine, Ausbilderzuordnung, Materialplanung.
- Portalkonten können **niemals**: Anwesenheit im Dienstbuch ändern, Qualifikationen oder Sonderaufgaben anlegen, ändern oder löschen, Notizen lesen oder schreiben, Gruppen-/Abteilungszuordnung ändern, sich selbst oder anderen Rollen geben, Daten nicht zugewiesener Personen sehen.
- Keine offene Selbstregistrierung (Entscheidung E1). Kein Portal-Zugriff auf Dienstbuch-Einträge ohne verknüpften geplanten Dienst.
- Keine Bezahl-, Chat- oder Dokumentenupload-Funktion für Portalkonten in diesem Umfang.

## 2. Getroffene Entscheidungen (Nutzer, 07.10.2026)

| ID | Frage | Entscheidung |
| --- | --- | --- |
| E1 | Kontoanlage | **Nur Einladung** durch Betreuende aus dem Eltern- bzw. Mitgliedsdatensatz. Einladungslink setzt das Passwort (gleicher Token-Mechanismus wie Passwort-Reset). |
| E2 | Änderungen an Namen/Kontakten | **Alles mit Freigabe.** Jede Änderung ist ein Änderungsantrag; erst die Freigabe übernimmt Werte. |
| E3 | Teilnahmemodus | **Je Dienst konfigurierbar**: „Abmeldung“ (alle erwartet), „Anmeldung“ (offen), „Zuteilung“ (bewerben, Verantwortliche teilen zu). Standard je Abteilung einstellbar. |
| E4 | Fristen | **Getrennte Fristen**: Anmeldeschluss und Abmeldeschluss, je Abteilung als Versatz vor Beginn voreingestellt, je Dienst überschreibbar. |
| E5 | Warteliste | **Je Dienst wählbar**: Standard automatisches Nachrücken nach Meldezeitpunkt (nur passende Personen für den freien Platz) mit Benachrichtigung; umstellbar auf manuell. Im Modus Zuteilung immer manuell. |
| E6 | Elternzugriff | **Endet mit 18.** Eltern- und Mitgliedskonto bestehen bis zur Volljährigkeit parallel; danach endet der Elternzugriff automatisch (Vorwarnung 30 Tage; Verlängerung nur durch Betreuende mit Begründung und Enddatum). |
| E7 | Freigabeebene | **Organisation setzt Vorgaben und Obergrenzen, Abteilungen** schränken innerhalb davon ein oder geben frei. Keine Einzelausnahmen je Person. |
| E8 | Benachrichtigung Betreuende | **In-App-Aufgaben** (immer) + **E-Mail sofort** + **Push** (neue Kategorie, freiwillig je Gerät). Je Benutzer abwählbar, außer In-App. |
| E9 | Dienstbuch-Übernahme | **Vorschlag + Ein-Klick**: eigene Meldespalte; „Abmeldungen als entschuldigt übernehmen“ nur für Personen ohne erfasste Anwesenheit; nie automatisch. |
| E10 | Teilnehmende | **Mitgliedsdatensätze**. Benutzerkonten (Betreuende, Einsatzkräfte) werden mit ihrem Mitgliedsdatensatz verknüpft; Qualifikationen aus beiden Quellen zählen. |
| E11 | Prüfzeitpunkt Voraussetzungen | **Gültigkeit am Diensttag.** Fehlt eine Voraussetzung, ist die Meldung mit Begründung gesperrt; läuft sie nachträglich ab oder wird entzogen, wird die Meldung als Konflikt markiert und der Verantwortliche benachrichtigt. |
| E12 | Quick-Action-Links | **Gemischt.** Ein Link wirkt nur nach Login und nur für das adressierte Konto. Folgenlose Aktionen (Ansicht öffnen, als gelesen markieren) laufen nach dem Login direkt; alles mit Wirkung auf Daten, Teilnahme oder Aufgabenstatus zeigt eine vorausgefüllte Bestätigung. |
| E13 | Bindung Verwaltendenkonto ↔ Mitglied | **Benutzerverwaltung verknüpft 1:1, das Konto bestätigt** die Verknüpfung beim nächsten Login. Bis dahin „ausstehend“ ohne Wirkung. |
| E14 | Eigene Daten verknüpfter Verwaltender | **Direkt mit vorhandenen Rechten, als „Eigenänderung“ protokolliert.** Qualifikationen und Sonderaufgaben am eigenen Datensatz legt immer eine andere Person an, ändert oder löscht sie (Vier-Augen). |
| E16 | Mitteilungen zum eigenen Teilnahmestatus | Bei **Zuteilung, Nicht-Berücksichtigung, Platz auf der Warteliste und Nachrücken** erhalten die Betroffenen **E-Mail und Push**, sofern nicht in den eigenen Einstellungen deaktiviert (Nutzerangabe 07.10.2026). |
| E17 | Abmeldelink | **Jede Teilnahme-E-Mail enthält immer einen Abmeldelink** passend zum Status (Abmelden, Von der Warteliste abmelden, Bewerbung zurückziehen); er funktioniert nach Login mit Bestätigung (E12). Zusätzlich enthält jede E-Mail den Link zu den Benachrichtigungseinstellungen (Nutzerangabe 07.10.2026). |
| E15 | Status im Eingang | **Team + persönlich.** Aufgaben haben einen teamweiten Status (offen/erledigt mit Name und Zeit); Hinweise einen persönlichen Gelesen-Status. |
| E18 | Aufbauende Qualifikationen | **Höhere Qualifikationen schließen niedrigere ein** (Nutzerangabe 08.10.2026): Wer „Truppmann“ voraussetzt, lässt auch „Truppführer“ zu. Qualifikationstypen erhalten „schließt ein“ (transitiv, zyklenfrei, in der Qualifikationsverwaltung gepflegt). Umsetzung als PART-03.7 vor PART-04. |

### 2.1 Vom Konzept festgelegte Standards (änderbar, aber vorbelegt)

| ID | Festlegung | Begründung |
| --- | --- | --- |
| D1 | Teilnahme hängt an `TrainingSession`, nicht an `Service`. | Nur geplante Dienste sind meldefähig; Dienstbuch bleibt reine Dokumentation. Manuell im Dienstbuch angelegte Dienste haben keine Meldungen. |
| D2 | Ein Mitglied ist portalberechtigt, wenn **mindestens eine** seiner aktiven Abteilungen das Mitgliederportal für sein Alter erlaubt. Sichtbare Daten und Dienste werden trotzdem je Abteilung gefiltert. | Mehrfachmitgliedschaft (z. B. Jugend + Einsatz) darf nicht zu Ausschluss führen; Datenfreigaben bleiben abteilungsscharf. |
| D3 | Mitgliederportal-Modus je Abteilung: `aus` · `ab Alter N` · `alle`. Organisationsstandard `aus`. Ohne Geburtsdatum gilt „ab Alter N“ als nicht erfüllt. | Datenschutzfreundlicher Standard. |
| D4 | Abmeldegrund nur als Kategorie (Krankheit, Schule/Beruf, Urlaub, Familie, Sonstiges) plus optionaler Kurztext ≤ 200 Zeichen mit Hinweis „Keine Gesundheitsdetails angeben“. Kurztext sehen nur Dienstverantwortliche, er wird 90 Tage nach Dienstende gelöscht. | Datenminimierung (Art. 5 DSGVO), Gesundheitsdaten vermeiden. |
| D5 | „Abmeldung“-Modus kennt weder Höchstzahl noch Warteliste noch Positionen. Positionen und Höchstzahl setzen „Anmeldung“ oder „Zuteilung“ voraus. | Erwartete Teilnahme aller Gruppenmitglieder widerspricht begrenzten Plätzen. |
| D6 | Portal zeigt bei begrenzten Diensten nur freie Plätze und eigene Wartelistenposition, niemals Namen anderer. | Datenschutz. |
| D7 | Zeitraum-Abmeldung („Ich bin vom … bis … verhindert“) meldet in einem Schritt von allen geplanten Diensten im Zeitraum ab, deren Abmeldeschluss noch nicht erreicht ist; Vorschau vor Bestätigung. | Typischer Elternfall (Urlaub, Krankheit). |
| D8 | Nach Dienstbeginn sind Meldungen eingefroren. Betreuende können bis Beginn auch nach Fristende für Personen melden/abmelden (gekennzeichnet „nach Frist durch Betreuende“). | Klare Trennung Planung ↔ Dokumentation. |
| D9 | Wer prüft Änderungsanträge: Konten mit der neuen Berechtigung `portal.review_changerequest` in einer Abteilung der betroffenen Person (bei Eltern: Abteilungen der zugewiesenen Kinder). Standardrollen Jugendwart und Abteilungsjugendwart erhalten sie bei Neuinstallation; bestehende Gruppen nur über den ROLE-01-Vorlagenvergleich. | Rollenmodell ROLE-01 bleibt Quelle; keine stille Rechteerweiterung. |
| D10 | Dienstverantwortliche eines geplanten Dienstes: `TrainingSession.created_by` plus Übungsleitung des verknüpften Dienstes; zusätzlich alle mit `can_manage_training` in der Abteilung als Vertretung (nur In-App). | Benachrichtigung trifft die tatsächlich Zuständigen ohne Massen-E-Mail. |

### 2.2 Offene Fragen an den Nutzer (vor dem jeweiligen Paket klären)

| ID | Frage | Vorschlag | Betrifft |
| --- | --- | --- | --- |
| Q1 | Sollen Eltern Kinder anmelden dürfen, deren Gruppe/Abteilung nicht zum Dienst gehört, wenn der Dienst „für alle der Abteilung“ geöffnet ist? | Ja, Zielgruppe = Gruppen des Dienstes; ohne Gruppen = ganze Abteilung. | PART-01 |
| Q2 | Darf ein Elternteil die Einladung an ein Mitgliedskonto des eigenen Kindes anstoßen (nicht versenden)? | **Entschieden 08.10.2026:** Nein in Version 1; nur Betreuende laden ein. | PORTAL-01 |
| Q3 | Sollen Mitglieder im Modus „Zuteilung“ eine Wunschposition angeben dürfen? | Ja, optional; Standard „beliebige passende Position“. | PART-04 |
| Q4 | Sollen Verwaltendenkonten zusätzlich an einen **Elterndatensatz** gebunden werden können (Verwaltende mit Kindern in der Jugend)? | Ja, gleiche Verknüpfungstabelle und gleiche Bestätigung; im Verwaltungslayout erscheint dann „Meine Kinder“. | PORTAL-04 |
| Q5 | Gültigkeit von Quick-Action-Links | 14 Tage, bei Teilnahmeaktionen höchstens bis Dienstbeginn, bei Antragsaktionen bis zur Entscheidung. | NOTIF-01 |

## 3. Ausgangslage im Code (geprüft am 07.10.2026)

| Bereich | Befund | Folge für das Konzept |
| --- | --- | --- |
| Konten | `users.CustomUser` (AbstractUser, `auth_source`, MFA, Passkeys, `UserSession`). **Keine Verknüpfung** zu `members.Member` oder `members.Parent`. | Neue Verknüpfungstabelle `portal.AccountLink`; neues Feld `CustomUser.account_kind`. |
| Eltern | `members.Parent` mit `children = M2M(Member)`, Kontaktfeldern und `notes`. | Elternzugriff wird aus `Parent.children` abgeleitet; keine zweite Zuordnung. |
| Mitglieder | `members.Member` mit `gender` (male/female/diverse), `birthday`, `departments` (M2M), `group`, `status`, `notes`. | Geschlechts-/Alters-/Gruppenregeln nutzen vorhandene Felder. |
| Geplante Dienste | `training.TrainingSession` mit Status draft/published/completed/cancelled, `groups`, `department`, Serienfeldern, `revision`. `training/workflow.py:sync_linked_service` legt bei Veröffentlichung den `servicebook.Service` an. | Teilnahme an `TrainingSession`; Dienstbuch liest Meldungen über `Service.training_session`. |
| Dienstbuch | `Service` (Thema, Ort, `events` = besondere Vorkommnisse), `Attendance` (Member, A/E/F), `StaffAttendance` (CustomUser). | Keine Schemaänderung an Anwesenheit; Meldestatus wird nur gelesen und optional als „E“ übernommen. |
| Qualifikationen | `qualifications.Qualification` mit `type`, `user` **oder** `member`, `date_acquired`, `date_expires`; `SpecialTask` analog. | Regelauswertung vereinigt Mitglieds- und verknüpfte Kontoqualifikationen (E10). |
| Passwort-Reset | `users/tokens.py` (`PasswordResetTokenGenerator`), Endpunkte `request_password_reset`/`reset_password` in `users/api_views.py`, Views `PasswordResetRequestView.vue`/`PasswordResetConfirmView.vue`. | Einladung nutzt denselben Generator und dieselbe Bestätigungsseite (Modus „Passwort festlegen“). |
| Rechte | `DEFAULT_PERMISSION_CLASSES = CustomDefaultPermissions`; einige Views nur mit `IsAuthenticated` (u. a. `jf_manager_backend/dashboard_api.py`, `jf_manager_backend/api_views.py`, `members/api/viewsets/attachment_viewsets.py`, `settings_manager/api/viewsets/__init__.py`, `notifications/views.py`, Teile von `users/api_views.py`). | **Sicherheitskritisch:** Portalkonten müssen global von allen Betreuenden-Endpunkten ausgeschlossen werden (Abschnitt 5.2). |
| Push | `notifications.PushSubscription` mit Kategorien `services`, `orders`. | Neue Kategorien `requests` (Betreuende) und `participation` (Portal und Betreuende). |
| Design | DES-01-Tokens: Grund `#F5F7FA`, Flächen weiß, Text `#172033`, Akzent Feuerwehrrot `#B91C1C` (je Organisation anpassbar), Systemschrift, 8-px-Raster, Touchflächen ≥ 44 px. | Mockups und Umsetzung nutzen dieselben Tokens; Portal ist mobil zuerst. |

## 4. Fachkonzept

### 4.1 Rollen und Sichtbarkeit

| Akteur | Darf | Darf nie |
| --- | --- | --- |
| Elternteil (Portal) | Eigene Daten (Elterndatensatz) und Daten zugewiesener, minderjähriger Kinder gemäß Freigabe sehen; Änderungsanträge stellen; Kinder zu geplanten Diensten an-/abmelden, bewerben, Wartelistenplatz zurückgeben; Zeitraum-Abmeldung; eigene Meldehistorie sehen. | Siehe 1.2; außerdem keine anderen Kinder, keine Kinder ab 18 (E6), keine anderen Elternteile des Kindes, sofern nicht freigegeben. |
| Mitglied (Portal) | Eigene Daten gemäß Freigabe; Änderungsanträge; sich selbst an-/abmelden/bewerben. | Siehe 1.2. |
| Verwaltende mit gebundenem Mitglied (PORTAL-04) | Wie bisher plus „Meine Dienste“ und „Meine Daten“ über den 1:1 gebundenen Mitgliedsdatensatz. Meldet sich selbst über dieselbe Teilnahme-API; ändert eigene Stammdaten direkt (protokolliert, E14). | Eigene Qualifikationen/Sonderaufgaben anlegen, ändern, löschen; eigene Änderungsanträge freigeben (Vier-Augen). |
| Dienstverantwortliche | Teilnahme konfigurieren, für Personen melden, Warteliste steuern, zuteilen, Meldungen im Dienstbuch sehen. | Anwesenheit ohne Dienstbuchrecht ändern. |
| Prüfende (`review_changerequest`) | Änderungsanträge in eigenen Abteilungen freigeben/ablehnen, auch feldweise. | Anträge außerhalb ihrer Abteilungen sehen. |
| Organisationsverwaltung | Portal-Obergrenzen, Mitgliederportal-Standard, Fristen-/Modusstandards, Vorlagen (organisationsweit). | — |

### 4.2 Datenkategorien und Freigaben (E7)

Jede Kategorie hat je Zielgruppe (Eltern / Mitglieder) einen Wert `verborgen` oder `sichtbar`. Die Organisation setzt **Obergrenze** (`erlaubt`/`gesperrt`) und **Standard**; Abteilungen setzen innerhalb der Obergrenze. Effektiver Wert für eine Person = sichtbar, wenn in **der Abteilung, aus der die Daten stammen**, sichtbar. Für personenbezogene Stammdaten ohne Abteilungsbezug (Name, Kontakt) gilt: sichtbar, wenn in mindestens einer gemeinsamen Abteilung sichtbar.

| Kategorie | Inhalt | Standard Eltern | Standard Mitglied | Hinweis |
| --- | --- | --- | --- | --- |
| Stammdaten & Kontakt | Vor-/Nachname, Adresse, Telefon, Mobil, E-Mail | immer sichtbar | immer sichtbar | Voraussetzung für Änderungsanträge; nicht abschaltbar. |
| Geburtsdatum | `birthday` | sichtbar | sichtbar | Nur lesend. |
| Gruppe & Abteilung | `group`, `departments` | sichtbar | sichtbar | |
| Mitgliedschaft | `status`, `joined` | verborgen | verborgen | |
| Ausweis | `identityCardNumber`, `avatar` | verborgen | verborgen | Bild über privaten Medienendpunkt (SEC-05). |
| Schwimmfähigkeit | `canSwimm` | verborgen | verborgen | |
| Qualifikationen | Typ, erworben, gültig bis (keine `note`, kein `issued_by`) | sichtbar | sichtbar | Nur lesend. |
| Sonderaufgaben | Aufgabe, Zeitraum (keine `note`) | verborgen | verborgen | Nur lesend. |
| Ausrüstung | Aktuell ausgegebene Inventarartikel (Name, Variante, Ausgabedatum) | verborgen | verborgen | Nur lesend. |
| Weitere Kontaktpersonen | Andere Elternteile des Kindes (Name, Telefon) | verborgen | — | |
| Meldehistorie | Eigene An-/Abmeldungen | immer sichtbar | immer sichtbar | Keine Anwesenheit. |
| *Bemerkungen, Ereignisse, Anhänge, Anwesenheit, Statistiken* | — | **nie** | **nie** | Nicht konfigurierbar, technisch nicht serialisiert. |

### 4.3 Konten, Einladung und Lebenszyklus (PORTAL-01)

Zustände eines Portalzugangs: `eingeladen` → `aktiv` → (`gesperrt` | `beendet`). Einladung abgelaufen → `eingeladen (abgelaufen)`, erneut sendbar.

- Einladung aus Elterndetail, Mitgliederdetail oder Sammelaktion (Liste ausgewählter Eltern). Pflicht: E-Mail-Adresse am Datensatz; Mitglied nur, wenn portalberechtigt (D2/D3).
- Einladungsmail: neutrale Vorlage mit Organisationsname, Ablauf 7 Tage, Link auf `/passwort-festlegen?token=…`. Gleicher Token-Generator wie Passwort-Reset, eigener Zweck-Salt (`portal-invite`).
- Annahme: Passwort setzen (gleiche Passwortrichtlinie), Datenschutzhinweis bestätigen (`dsgvo_external`), optional MFA/Passkey einrichten. Benutzername = E-Mail-Adresse (eindeutig). Existiert bereits ein Konto mit der Adresse, wird **kein** zweites angelegt: Betreuende sehen „Konto existiert, Verknüpfung hinzufügen?“ und die Verknüpfung wird erst nach Anmeldung des bestehenden Kontos bestätigt.
- Ein Konto kann gleichzeitig Elternteil (mehrere Kinder über einen `Parent`) und Mitglied sein (ein `Member`). Ein Betreuendenkonto kann einen Mitgliedsdatensatz verknüpfen (E10), ist aber kein Portalkonto.
- Elternzugriff je Kind endet am 18. Geburtstag 00:00 Ortszeit (täglicher Job). 30 Tage vorher: Hinweis an Elternteil und Mitglied; Betreuende sehen „Elternzugriff endet“ in der Aufgabenliste mit Aktion „Mitglied einladen“. Verlängerung: `ParentAccessExtension` mit Enddatum (max. 12 Monate) und Begründung.
- Entzug: Betreuende beenden Zugang; Sitzungen des Kontos werden sofort widerrufen (`UserSession`). Beendete Konten ohne verbleibende Verknüpfung werden deaktiviert (`is_active=False`), nicht gelöscht; Löschung folgt dem bestehenden Lösch-/Anonymisierungsrecht.
- Anmeldung: dieselbe Login-Seite. Session-API liefert `account_kind` und `portal`-Fähigkeiten; das Frontend leitet Portalkonten auf `/portal`. Sitzungsdauer der normalen Konten (30 Tage Inaktivität, max. 90 Tage). MFA optional, Passkeys verfügbar.
- LDAP/OIDC: Portalkonten sind immer lokal (`auth_source=local`). Ein OIDC-Login darf kein Portalkonto übernehmen.

### 4.4 Änderungsanträge (PORTAL-03, E2)

- Antragsfähige Felder: Member: `name`, `lastname`, `email`, `phone`, `mobile`, `street`, `zip_code`, `city`. Parent: zusätzlich `email2`. Nichts sonst (kein Geburtsdatum, keine Gruppe).
- Je Zielperson höchstens **ein offener Antrag**. Erneutes Bearbeiten aktualisiert den offenen Antrag (neue Version, Zeitstempel), solange er nicht in Prüfung gesperrt ist; Zurückziehen möglich.
- Antrag speichert für jedes Feld `alt` (Wert bei Antragstellung) und `neu`. Prüfansicht zeigt zusätzlich `aktuell`; weicht `aktuell` von `alt` ab, wird das Feld als Konflikt markiert und muss ausdrücklich bestätigt werden.
- Entscheidung feldweise: übernehmen / ablehnen, mit optionaler Begründung an den Antragsteller. Status: `offen`, `teilweise übernommen`, `übernommen`, `abgelehnt`, `zurückgezogen`.
- Übernahme ist eine atomare Transaktion mit Sperre auf dem Zieldatensatz und schreibt ein Änderungsprotokoll (wer, wann, Feld, alt, neu, Antrag).
- Validierung serverseitig: E-Mail-Format, Telefonnummer (Ziffern, `+`, Leerzeichen, `/`, `-`), PLZ-Länge, Längenlimits der Modellfelder, Entfernen von HTML und Steuerzeichen, Formel-Präfixe bleiben Text (SEC-08).
- Benachrichtigung Prüfende sofort (E8); Antragsteller erhält Entscheidung per E-Mail und im Portal.
- Änderung der E-Mail des eigenen Elterndatensatzes ändert **nicht** automatisch die Login-E-Mail; Login-E-Mail wird im Profil mit Bestätigungslink geändert.

### 4.5 Teilnahme an geplanten Diensten (PART-01)

**Meldefähig** ist eine `TrainingSession` mit `status=published`, Beginn in der Zukunft und `participation.portal_visible=True` (Standard an). Entwürfe, abgesagte und abgeschlossene Dienste sind nicht meldefähig; abgesagte erscheinen im Portal als „abgesagt“ mit eingefrorenem Status.

**Zielgruppe** eines Dienstes: Mitglieder der `groups` des Dienstes; ohne Gruppen alle aktiven Mitglieder der Abteilung. Zusätzlich müssen die Voraussetzungen (PART-03) erfüllt sein.

**Modi (E3):**

| Modus | Ohne Meldung | Aktionen Portal | Plätze/Positionen |
| --- | --- | --- | --- |
| Abmeldung | „erwartet“ | Abmelden (mit Grund), Abmeldung zurücknehmen | nein (D5) |
| Anmeldung | „keine Rückmeldung“ | Anmelden (ggf. Position wählen), Abmelden, Wartelistenplatz zurückgeben | optional Höchstzahl, Positionen, Warteliste |
| Zuteilung | „keine Rückmeldung“ | Bewerben (ggf. Wunschposition), Bewerbung zurückziehen, nach Zuteilung abmelden | Positionen/Höchstzahl, Verantwortliche teilen zu |

**Meldestatus** (`Registration.state`):

| Status | Anzeige Portal | Anzeige Dienstbuch |
| --- | --- | --- |
| `registered` | Angemeldet | angemeldet |
| `waitlisted` | Warteliste, Platz *n* | Warteliste (n) |
| `applied` | Beworben | beworben |
| `assigned` | Zugeteilt als *Position* | zugeteilt: Position |
| `not_selected` | Nicht berücksichtigt | nicht berücksichtigt |
| `cancelled` | Abgemeldet | abgemeldet (Grundkategorie) → Vorschlag „E“ |
| *(keine Zeile, Modus Abmeldung)* | Erwartet | erwartet |
| *(keine Zeile, sonst)* | Keine Rückmeldung | keine Rückmeldung |

Zusätzlich je Meldung: `conflict` (Voraussetzung am Diensttag nicht mehr erfüllt, E11), `late` (nach Frist durch Betreuende), `source` (`portal_parent`, `portal_member`, `staff`).

**Fristen (E4):** `registration_closes_at` (Anmeldeschluss; gilt für Anmelden/Bewerben) und `cancellation_closes_at` (Abmeldeschluss; gilt für Abmelden, Bewerbung zurückziehen, Wartelistenplatz zurückgeben). Standard je Abteilung als Versatz in Stunden vor Beginn (Organisationsstandard: Anmeldung 48 h, Abmeldung 2 h). Optional `registration_opens_at` (Standard: Veröffentlichung). Nach Abmeldeschluss zeigt das Portal „Abmeldung nur noch direkt bei der Dienstleitung“ mit den freigegebenen Kontaktwegen der Verantwortlichen.

**Serien:** Meldung je Termin. Zeitraum-Abmeldung (D7). Änderung von Datum/Zeit eines Termins mit Meldungen: Meldungen bleiben, Betroffene werden benachrichtigt; neue Fristen gelten ab Änderung; im Modus Anmeldung werden Gemeldete nicht automatisch abgemeldet.

**Nebenläufigkeit:** Platzvergabe innerhalb einer Transaktion mit `select_for_update` auf der `TrainingSession`-Zeile (PostgreSQL). Optimistische Version (`Registration.version`) für Betreuendenänderungen. Erwartete Größenordnung ≤ 50 Meldungen je Dienst; keine Paginierung im Board nötig, API dennoch begrenzt (≤ 500).

### 4.6 Voraussetzungen und Regel-Konfigurator (PART-03)

**Regelsprache** (JSON, versioniert, serverseitig validiert, maximal zwei Ebenen):

```json
{
  "v": 1,
  "match": "all",
  "rules": [
    {"kind": "qualification", "op": "has_all", "values": [12, 15]},
    {"kind": "qualification", "op": "has_any", "values": [7, 8]},
    {"kind": "gender", "op": "in", "values": ["female", "diverse"]},
    {"kind": "age", "op": "between", "min": 10, "max": 17},
    {"kind": "group", "op": "in", "values": [3, 4]},
    {"kind": "status", "op": "in", "values": [1]},
    {"kind": "special_task", "op": "has_any", "values": [2]},
    {"match": "any", "rules": [ … eine weitere Ebene ohne Verschachtelung … ]}
  ]
}
```

- `kind`: `qualification`, `special_task` (`has_any`, `has_all`, `has_none`), `gender` (`in`), `age` (`min`, `max`, `between`; Alter am Diensttag), `group`, `status`, `department` (`in`).
- Qualifikation gilt, wenn `date_acquired ≤ Diensttag` und (`date_expires` leer oder `≥ Diensttag`) — für `Qualification.member` und für `Qualification.user` eines verknüpften Kontos (E10).
- Aufbauende Qualifikationen (E18): Eine Bedingung auf Typ T ist auch durch jeden Typ erfüllt, der T direkt oder über Zwischenstufen einschließt (z. B. Zugführer → Gruppenführer → Truppführer → Truppmann), sofern diese höhere Qualifikation am Diensttag gültig ist. `has_none` schließt entsprechend auch höhere Qualifikationen aus. Begründungen und Vorschau nennen die ersetzende Qualifikation („erfüllt durch ‚Truppführer‘“); die Klartext-Zusammenfassung zeigt „Truppmann (oder höher)“. Die Hierarchie wird beim Auswerten einmal als Abschluss (transitive Hülle) geladen, ohne zusätzliche Abfragen je Person.
- Fehlende Daten (kein Geburtsdatum, kein Geschlecht) erfüllen die Regel nicht; die Begründung nennt die fehlende Angabe.
- Auswertung `participation/eligibility.py: evaluate(rule, member, on_date) -> Result(ok, reasons[])`, reine Funktion mit vorab geladenen Qualifikationen (keine N+1-Abfragen; Zielgruppe ≤ einige hundert).
- Begründungen sind verständliche Sätze: „Qualifikation ‚Maschinist‘ fehlt“, „Gültig nur bis 03.10.2026“, „Nur für Teilnehmende von 10 bis 17 Jahren“. Portal zeigt Begründungen nur für die eigene/zugewiesene Person.
- Geschlechtsregeln werden im Portal neutral formuliert („Dieser Dienst richtet sich an eine bestimmte Teilnehmendengruppe“) plus konkrete Begründung für die eigene Person.
- Nachprüfung (E11): täglicher Job und Ereignisse (Qualifikation geändert/gelöscht, Geburtsdatum/Gruppe geändert) prüfen alle aktiven Meldungen kommender Dienste neu; Verstöße setzen `conflict=True` und erzeugen eine Aufgabe für die Dienstverantwortlichen. Keine automatische Abmeldung.

**Konfigurator (UI):**

1. Abschnitt „Wer darf teilnehmen?“ mit Satzbau: *Teilnehmen dürfen Personen, die* **alle** / **mindestens eine** *der folgenden Bedingungen erfüllen.*
2. Bedingungszeile: `[Art ▾] [Operator ▾] [Werte (Mehrfachauswahl mit Suche) ]  [Entfernen]`. Art-Liste mit Symbolen: Qualifikation, Sonderaufgabe, Geschlecht, Alter, Gruppe, Status, Abteilung.
3. „Bedingungsgruppe hinzufügen“ erzeugt eine eingerückte Untergruppe mit eigenem alle/eine-Schalter (max. eine Ebene tiefer).
4. **Live-Vorschau** rechts: „18 von 41 Personen der Zielgruppe erfüllen die Voraussetzungen“, aufklappbare Liste „Ausgeschlossen“ mit Begründung je Person; Hinweis bei 0 Treffern.
5. Klartext-Zusammenfassung unter dem Konfigurator („Maschinist **und** (Gruppenführer **oder** Zugführer), Alter ab 18“).
6. „Als Vorlage speichern“ / „Vorlage anwenden“ (gemeinsam mit Positionen, 4.7).
7. Tastaturbedienung vollständig, Fehler direkt an der Zeile (z. B. „Mindestalter größer als Höchstalter“).

### 4.7 Plätze, Positionen, Mindestbesetzung, Warteliste, Zuteilung (PART-04)

**Begriffe:**

- **Höchstzahl** (`max_participants`): Obergrenze der angenommenen Meldungen (`registered`/`assigned`). Ohne Positionen einzige Kapazitätsgrenze.
- **Position** (`Slot`): benannte Funktion mit `min` (benötigt für Mindestbesetzung), `max` (Plätze), eigener Regel (Regelsprache 4.6) und Reihenfolge. Beispiel Brandsicherheitswache: „Wachführung“ min 1/max 1, Regel `has_all [Brandsicherheitswache, Gruppenführer]`; „Truppmann/-frau“ min 2/max 2, Regel `has_any [Truppmann Teil 1]`.
- **Allgemeine Voraussetzungen** gelten zusätzlich zu Positionsregeln.
- Sind Positionen definiert, ist die Höchstzahl = Summe der `max` (Feld wird abgeleitet und gesperrt angezeigt). Optional „Weitere Teilnehmende ohne Position“ mit eigener Platzzahl (z. B. Hospitierende).
- **Mindestbesetzung erreicht**, wenn jede Position mindestens `min` Zuteilungen hat. Anzeige: „Mindestbesetzung: 2 von 3 erfüllt – es fehlt 1× Wachführung“. Optional `min_participants` ohne Positionen.

**Modus Anmeldung mit Positionen:** Person wählt eine passende Position oder „beliebig“. Bei „beliebig“ ordnet der Server deterministisch zu: (1) Positionen unter `min` vor solchen über `min`, (2) Position mit den wenigsten passenden Kandidaten zuerst (Knappheit), (3) Reihenfolge der Positionen. Ist keine passende Position frei: Warteliste je Position (bei „beliebig“: auf allen passenden Positionen; der erste frei werdende Platz gewinnt).

**Warteliste (E5):** Reihenfolge nach Meldezeitpunkt. Nachrücken `auto`: Bei frei werdendem Platz rückt die erste wartende Person nach, die die Regel dieses Platzes erfüllt; Benachrichtigung an die Person (Portal, E-Mail, Push). Nachrücken endet mit Dienstbeginn. Nach Abmeldeschluss nachrückende Personen erhalten den Hinweis „kurzfristig nachgerückt“ und die Dienstverantwortlichen eine Sofortmeldung. `manual`: Verantwortliche erhalten Aufgabe „Platz frei – Warteliste prüfen“.

**Modus Zuteilung:** Personen bewerben sich (`applied`, optional Wunschposition). Zuteilungsboard (Desktop, Tablet):

- Links Bewerbungen mit Qualifikationschips und Kennzeichnung „passt für: Wachführung, Truppmann“; Filter „nur passend für …“; Sortierung nach Bewerbungszeit, Name, bisherigen Zuteilungen in den letzten 90 Tagen (Fairness-Hinweis, keine Anwesenheitsdaten).
- Rechts Positionen als Ablagefelder mit Plätzen (`min` hervorgehoben). Ziehen nur auf passende Positionen; unpassende Felder werden beim Ziehen ausgegraut mit Begründung. Alternative ohne Drag: Auswahl + „Zuteilen zu …“-Menü (Tastatur, Touch).
- Zuteilungen sind ein Entwurf bis „Zuteilung veröffentlichen“; dann erhalten Zugeteilte `assigned`, übrige `not_selected` (oder `applied` bleibt bei Option „Bewerbungen offen lassen“), alle werden benachrichtigt. Spätere Änderungen werden einzeln benachrichtigt.
- Konfliktschutz: Board lädt mit `participation_revision`; Speichern mit veralteter Revision liefert 409 mit Unterschied.

**Vorlagen (Besetzungsvorlage):** Name, Beschreibung, Geltung (Abteilung oder Organisation), Modus-Empfehlung, allgemeine Voraussetzungen, Positionen (Name, min, max, Regel), Höchstzahl, Wartelistenmodus. Anwenden kopiert den Stand in den Dienst (unabhängige Kopie wie TRAIN-03); Vorlagenänderungen wirken nicht auf bestehende Dienste. Vorlagenregeln referenzieren Qualifikations-IDs; gelöschte/archivierte Typen werden beim Anwenden als Warnung gemeldet. Vorlagen können auch in TRAIN-03-Übungsvorlagen und Serien übernommen werden: Serientermine erhalten je Termin eine Kopie.

### 4.8 Dienstbuch-Integration (PART-02, E9)

- Im Dienstbuch-Eintrag mit verknüpftem geplantem Dienst erscheint der Bereich **„Meldungen“** vor der Anwesenheitserfassung: Zähler (angemeldet, abgemeldet, Warteliste, keine Rückmeldung, Konflikte), Mindestbesetzungsstatus und Tabelle Person | Meldung | Grund (Kategorie) | gemeldet von/am | Anwesenheit.
- Aktion „Abmeldungen als entschuldigt übernehmen (n)“: setzt `Attendance.state='E'` nur für abgemeldete Personen **ohne** vorhandenen Anwesenheitswert, über die bestehende Einzeländerungs-API mit Konfliktprüfung; Vorschau-Dialog listet Betroffene.
- Anwesenheitserfassung zeigt den Meldestatus als kleinen Hinweis an jeder Person (Symbol + Text, nicht nur Farbe).
- Gemeldete Personen außerhalb der Zielgruppe (z. B. Gäste anderer Gruppen, zugeteilte Einsatzkräfte) erscheinen automatisch in der Anwesenheitsliste.
- Portalkonten haben keinen Lesezugriff auf `Service`, `Attendance`, `StaffAttendance`, besondere Vorkommnisse.

#### 4.8.1 Mobiles Dienstbuch (Hauptnutzung)

Das Dienstbuch wird nahezu ausschließlich auf dem Smartphone vor Ort genutzt. Die mobile Gestaltung ist deshalb die Referenz; der Desktop ist eine breitere Darstellung derselben Bausteine. Abstimmung mit UX-04 (mobile Erfassung, Status, Speicheranzeige): PART-02 liefert die Meldungsanteile, UX-04 die Erfassungsgrundlage. Wer zuerst umsetzt, legt die gemeinsamen Komponenten an; der andere Teil baut darauf auf.

| Ansicht | Inhalt und Bedienung |
| --- | --- |
| Liste | Abschnitte „Heute“, „Demnächst“, „Anwesenheit offen“ (vergangene Dienste ohne vollständige Erfassung). Karte je Dienst: Datum/Zeit, Thema, Gruppe(n), Zähler „erwartet · abgemeldet · erfasst“. Bei gebundenem Mitglied (PORTAL-04) zusätzlich der eigene Meldestatus. Hauptaktion auf der heutigen Karte: „Anwesenheit erfassen“. |
| Dienst · Meldungen | Vor Dienstbeginn: Zähler, Mindestbesetzung, Liste nach Status gruppiert (abgemeldet, angemeldet, Warteliste, keine Rückmeldung); Grundkategorie sichtbar, Kurztext nur nach Antippen. „Für Person melden/abmelden“ als Bottom-Sheet. |
| Dienst · Anwesenheit | Fixierte Kopfzeile mit Zählern und Filterchips (Alle, Offen, Abgemeldet, Gäste). Eine Zeile je Person: Name, Meldestatus als Text+Symbol, drei große Schaltflächen A/E/F (≥ 48 px, Daumenbereich). Vorschläge aus Abmeldungen gestrichelt. Einzelspeicherung je Antippen wie bisher, sichtbarer Speicher-/Abgleichstatus unten. |
| Übernahme-Sheet | „Abmeldungen als entschuldigt übernehmen“: Liste mit Häkchen (vorausgewählt nur ohne Anwesenheit), Anzahl im Button, Hinweis auf bereits erfasste Personen. |
| Dienst · Betreuende | Wie Anwesenheit für `StaffAttendance`; gebundene Verwaltende sehen „Ich bin da“ als Abkürzung. |
| Dienst · Vorkommnisse | Textfeld mit Autosave-Status; nie im Portal sichtbar. |

Regeln: Tab-Leiste oben (Meldungen · Anwesenheit · Betreuende · Vorkommnisse), unten die globale Modulnavigation; keine horizontale Scrollleiste; Personensuche oben in der Liste; Netzfehler sichtbar, nicht gespeicherte Antippaktionen rot markiert mit „Erneut versuchen“; kein Offline-Schreibmodus (Roadmap TRAIN-04/UX-04).

### 4.9 Benachrichtigungen, Eingang und E-Mail-Vorlagen (NOTIF-01, E8, E12, E15)

#### 4.9.1 Ereignisse und Kanäle

| Ereignis | Empfänger | Eingang | E-Mail (Vorlagentyp) | Push |
| --- | --- | --- | --- | --- |
| Änderungsantrag gestellt/aktualisiert | Prüfende der Abteilungen | Aufgabe „Anträge“ | sofort (`cr_submitted`) | `requests` |
| Antrag entschieden | Antragsteller | Portal-Hinweis | sofort (`cr_decided`) | `participation` |
| Abmeldung (alle Modi) | Dienstverantwortliche | Hinweis „Meldungen“, je Dienst gebündelt | sofort, wenn ≤ 48 h vor Beginn oder Mindestbesetzung gefährdet (`reg_cancelled`); sonst Tageszusammenfassung (`reg_digest`) | `participation` |
| Anmeldung/Bewerbung | Dienstverantwortliche | Hinweis „Meldungen“, gebündelt | nur Tageszusammenfassung (`reg_digest`, abwählbar) | — |
| Platz frei, Warteliste manuell | Dienstverantwortliche | Aufgabe „Besetzung“ | sofort (`slot_free_manual`) | `participation` |
| Mindestbesetzung gefährdet (≤ 48 h) | Dienstverantwortliche | Aufgabe „Besetzung“ | sofort (`staffing_at_risk`) | `participation` |
| Auf Warteliste gesetzt (Anmeldung oder Zuteilung) | Betroffene (E16) | Portal-Hinweis | sofort (`waitlist_placed`) | `participation` |
| Nachgerückt | Betroffene (E16) | Portal-Hinweis | sofort (`waitlist_promoted`) | `participation` |
| Zuteilung veröffentlicht: zugeteilt / nicht berücksichtigt | Betroffene (E16) | Portal-Hinweis | sofort (`assign_published`) | `participation` |
| Dienst geändert/abgesagt | Gemeldete, Wartende, Erwartete | Portal-Hinweis | sofort (`session_changed`) | `participation` |
| Voraussetzungskonflikt | Dienstverantwortliche | Aufgabe „Besetzung“ | sofort (`eligibility_conflict`) | `participation` |
| Einladung | eingeladene Person | — | sofort (`portal_invite`) | — |
| Einladung angenommen/abgelaufen | Einladende | Hinweis „Konten“ | — | — |
| Kontoverknüpfung ausstehend/bestätigt/abgelehnt (PORTAL-04) | betroffenes Konto / Verknüpfende | Hinweis „Konten“ | sofort an das Konto (`account_link`) | — |
| Elternzugriff endet in 30 Tagen | Elternteil, Mitglied; Betreuende | Hinweis / Aufgabe „Konten“ | einmalig (`parent_access_end`) | — |

**Betroffene** sind bei Kindern alle verknüpften, aktiven Elternkonten und, falls vorhanden, das eigene Mitgliedskonto; bei Erwachsenen das Mitgliedskonto bzw. das gebundene Verwaltendenkonto (PORTAL-04). Für die vier Teilnahmestatus (E16) sind E-Mail und Push standardmäßig **an** und je Konto in „Profil → Mitteilungen“ getrennt abschaltbar; Push setzt ein freiwillig registriertes Gerät voraus (bestehende PWA-Push-Logik, neue Kategorie `participation` auch für Portalkonten).

**Abmeldelink (E17):** Jede Teilnahme-E-Mail (`waitlist_placed`, `waitlist_promoted`, `assign_published`, `session_changed`) enthält einen statusabhängigen Abmeldelink als Quick Action mit Bestätigung:

| Status der Person | Abmeldelink | Wirkung nach Bestätigung |
| --- | --- | --- |
| angemeldet / zugeteilt / nachgerückt | „Abmelden“ | Abmeldung mit Grundauswahl; Platz wird frei, Warteliste rückt nach |
| Warteliste | „Von der Warteliste abmelden“ | Wartelistenplatz wird zurückgegeben |
| beworben / nicht berücksichtigt bei offener Nachbesetzung | „Bewerbung zurückziehen“ | Person wird bei Nachbesetzung nicht mehr berücksichtigt |
| nicht berücksichtigt, Zuteilung abgeschlossen | „Keine weiteren Nachrichten zu diesem Dienst“ | stummschaltet weitere Mitteilungen zu diesem Dienst |

Nach Ablauf des Abmeldeschlusses führt der Link zur Terminansicht mit dem Hinweis auf die direkte Kontaktaufnahme (4.5). Push-Mitteilungen enthalten keinen Abmeldelink, öffnen aber die Terminansicht mit derselben Aktion.

Regeln: Jede E-Mail-Art je Benutzer abwählbar (Eingang nicht). Sperrbildschirm-Texte ohne Namen. Zustellung über die bestehende Hintergrundwarteschlange, idempotent je Ereignis-ID. Die Sofort-Schwelle (48 h) ist je Abteilung einstellbar.

#### 4.9.2 Benachrichtigungseingang für Verwaltende

- **Ort:** eigener Menüpunkt „Eingang“ mit Zähler (offene Aufgaben + ungelesene Hinweise) in Desktop- und mobiler Navigation; Dashboard-Kachel zeigt die drei dringendsten Aufgaben.
- **Arten (E15):** *Aufgabe* (verlangt Handeln: Antrag prüfen, Platz besetzen, Konflikt lösen, Elternzugriff verlängern/Mitglied einladen) mit **Teamstatus** offen → erledigt (wer, wann, wodurch; automatisch erledigt, sobald die zugrunde liegende Sache erledigt ist, z. B. Antrag entschieden). *Hinweis* (Information: Abmeldungen, Einladung angenommen) mit **persönlichem** Gelesen-Status.
- **Bündelung:** Gleichartige Hinweise werden über einen Gruppenschlüssel zusammengefasst, z. B. `reg_cancelled:session:123` → „3 Abmeldungen · Knoten und Stiche, Di 14.10.“. Eine neue Abmeldung erhöht die Zahl, setzt den Eintrag nach oben und wieder auf ungelesen. Aufgaben werden nicht gebündelt.
- **Empfänger:** beim Erzeugen aus Abteilung und Berechtigung berechnet (D9/D10); beim Lesen wird die aktuelle Berechtigung erneut geprüft, entzogene Rechte blenden Einträge aus.
- **Filter:** Alle · Aufgaben · Hinweise; Kategorie (Anträge, Meldungen, Besetzung, Konten); Abteilung; „nur ungelesen“; „erledigte anzeigen“.
- **Aktionen direkt im Eintrag:** dieselben Aktionen wie die Quick Actions (4.9.4) inklusive Bestätigung, z. B. „Antrag prüfen“, „Platz besetzen“, „Abmeldungen ansehen“. Mehrfachauswahl für „als gelesen markieren“.
- **Aktualisierung:** beim Öffnen und alle 60 s bei sichtbarem Tab; Push-Mitteilungen öffnen den Eintrag.
- **Aufbewahrung:** erledigte und gelesene Einträge 180 Tage, dann löschen. Einträge enthalten Verweise und kurze Titel, keine Freitexte aus Anträgen oder Abmeldegründen.
- **Mobil:** Liste mit Kategorie-Chips, Eintragskarte mit Hauptaktion; Detail als Vollbild mit Aktionsleiste unten.

#### 4.9.3 E-Mail-Vorlagen über das bestehende Mail-Template-System

Basis ist das vorhandene System: `orders.EmailTemplate` (eindeutiger `template_type`, `subject_template`, `html_template`, `text_template` als Django-Template, `layout` none/general/important/events, `is_active`), `orders.EmailLayoutTemplate` (anpassbare Rahmen), `orders.notifications.template_service.TemplateRenderer` (Datenbankvorlage vor Dateivorlage, Cache) und der Variablenkatalog mit Beispieldaten in `settings_manager/api/viewsets/email_template.py` (`TEMPLATE_VARIABLES`, Vorschau in den Einstellungen).

Erweiterung:

1. Neue `template_type`-Werte (Feldlänge 20 beachten): `portal_invite`, `account_link`, `cr_submitted`, `cr_decided`, `reg_cancelled`, `reg_digest`, `slot_free_manual`, `staffing_at_risk`, `waitlist_promoted`, `assign_published`, `session_changed`, `eligibility_conflict`, `parent_access_end`. Choices-Migration in `orders`.
2. Standardvorlagen als Dateien unter `backend/templates/notifications/emails/<typ>.html` und `<typ>.txt`, eingetragen in `TemplateRenderer.DEFAULT_TEMPLATES`. Eine Datenbankvorlage desselben Typs überschreibt sie; „Auf Standard zurücksetzen“ löscht die Datenbankvorlage.
3. Variablenkatalog je Typ mit Beispieldaten in `TEMPLATE_VARIABLES` (empfohlen: Katalog in ein eigenes Modul `notifications/email_catalog.py` verschieben und dort registrieren lassen, damit Portal-/Teilnahme-Apps eigene Typen ohne Änderung der Settings-View ergänzen).
4. **Kontext nur aus vorbereiteten, flachen Werten** (Zeichenketten, Zahlen, Listen von Dicts), keine Modellinstanzen: Django-Templates dürfen keine Methoden oder Relationen der Modelle erreichen. Alle Werte werden automatisch maskiert; HTML entsteht nur aus Vorlage und Layout, Ergebnis läuft durch `sanitize_rich_html` (SEC-04).
5. Pflichtbestandteile je Vorlage (Validierung beim Speichern): mindestens ein Link `{{ links.open }}` und der Link zu den Benachrichtigungseinstellungen `{{ links.preferences }}`; bei Teilnahmevorlagen zusätzlich der Abmeldelink `{{ links.withdraw }}` mit `{{ links.withdraw_label }}` (E17). Fehlen sie, wird die Speicherung mit Feldfehler abgelehnt.
6. Gemeinsame Variablen aller Typen: `org.name`, `org.color`, `recipient.first_name`, `recipient.kind` (staff/parent/member), `links.open`, `links.preferences`, `links.withdraw` + `links.withdraw_label` (nur Teilnahmevorlagen, statusabhängig), `links.inbox` (nur Verwaltende), `actions` (Liste `{label, url, style}` – siehe 4.9.4), `sent_at`.
7. Kein Inhalt aus Abmeldegrund-Kurztexten, Anträgen oder Notizen in E-Mails an Verwaltende über Feldnamen und Kategorie hinaus; Antragswerte (alt → neu) nur für Kontaktfelder und nur an Prüfende.

Typspezifische Variablen und Standardtexte: Anhang A.

#### 4.9.4 Quick-Action-Links (E12)

- **Form:** `https://<host>/a/<token>`. Token = `django.core.signing.dumps({"u": user_id, "k": aktion, "o": {Objekt-IDs}, "n": nonce}, salt="jf.notify.action.v1")`, kompakt, signiert, zeitlich begrenzt (Q5). Keine personenbezogenen Daten außer IDs.
- **Ablauf:** Frontend-Route `/a/:token` ist ohne Anmeldung erreichbar. Ohne Sitzung → `/login?next=/a/<token>` (Login, MFA, Passkey wie gewohnt; `next` nur als relativer Pfad mit einem führenden `/` akzeptiert). Mit Sitzung → `POST /api/v1/actions/resolve/` (CSRF) prüft Signatur, Ablauf, **Konto = adressiertes Konto** (sonst Hinweis „Dieser Link gehört zu einem anderen Konto“), Existenz des Objekts und die **aktuellen** Rechte. Antwort: Aktionsart, Modus `direct`/`confirm`, Zielroute, Vorschau.
- **Direkt (folgenlos):** Ansicht öffnen, Hinweis als gelesen markieren, Benachrichtigungsart abbestellen (mit Rückgängig).
- **Mit Bestätigung:** Anmelden, Abmelden (mit Grundauswahl), Bewerbung zurückziehen, Antrag übernehmen/ablehnen (alle Felder oder Prüfansicht), Platz aus Warteliste besetzen, Abmeldungen als entschuldigt übernehmen, Aufgabe als erledigt markieren.
- **Ausführung** immer per `POST` aus der angemeldeten Oberfläche, nie durch den Linkaufruf selbst (Mail-Scanner und Linkvorschauen lösen nichts aus). Aktionen sind Zielzustände und damit idempotent; ist der Zustand bereits erreicht oder durch andere geändert („Antrag bereits von A. Keller entschieden“), zeigt die Bestätigungsseite den aktuellen Stand statt eines Fehlers.
- **Abgelaufen/ungültig:** freundliche Seite mit Link zur Zielansicht; keine Angabe, ob das Objekt existiert.
- **Protokoll:** Ausführungen über Quick Actions tragen `via=email_action` im Ereignisverlauf.

### 4.10 Verwaltendenkonto als Mitglied (PORTAL-04, E13, E14)

In vielen Feuerwehren und Vereinen sind Verwaltende selbst Mitglied. Ihr Verwaltungskonto wird deshalb 1:1 an ihren Mitgliedsdatensatz gebunden, statt ein zweites Portalkonto anzulegen.

- **Bindung:** Benutzerverwaltung (Systemadministration oder Rolle mit Kontoverwaltung) oder Mitgliederdetail „Konto verknüpfen“. Vorschläge nach gleicher E-Mail-Adresse bzw. Name; je Konto höchstens ein Mitglied und je Mitglied höchstens ein Konto (Datenbank-Eindeutigkeit beidseitig). Ein Mitglied mit Portalkonto kann nicht zusätzlich an ein Verwaltendenkonto gebunden werden; Umwandlung nur durch Systemadministration (Portalkonto wird beendet, Verknüpfung übertragen).
- **Bestätigung (E13):** Die Verknüpfung ist „ausstehend“, bis das Konto sie beim nächsten Login bestätigt: Zwischenschritt „Ist das dein Mitgliedsdatensatz?“ mit Name, Geburtsjahr, Abteilung, Gruppe; Schaltflächen „Ja, das bin ich“ / „Nein, nicht meiner“. Ablehnung erzeugt einen Hinweis für die Verknüpfende Person. Ausstehende Verknüpfungen haben keine Wirkung.
- **Wirkung nach Bestätigung:**
  - „Meine Dienste“ (eigene Meldungen, Anmelden/Abmelden über dieselbe Teilnahme-API) und „Meine Daten“ im normalen Verwaltungslayout, mobil als eigener Bereich im Dienstbuch und auf dem Dashboard.
  - Teilnahmevoraussetzungen werten Qualifikationen des Mitglieds **und** des Kontos aus (E10). Beim Bestätigen zeigt die Verwaltung mögliche Doppelungen (gleicher Typ an Konto und Mitglied) mit Aktion „zusammenführen“ (Nachweis bleibt am Mitglied); nie automatisch.
  - Dienstbuch: dieselbe Person erscheint je Dienst **entweder** als Teilnehmende (`Attendance`) **oder** als Betreuende (`StaffAttendance`); die Oberfläche bietet „als Teilnehmende/r · als Betreuer/in“ und verhindert beides gleichzeitig. Auswertungen zählen die Person einmal.
  - Zuteilungsboard: Selbstzuteilung möglich, wird gekennzeichnet und protokolliert.
- **Eigene Daten (E14):** Stammdaten des eigenen Mitglieds mit vorhandenen Rechten direkt änderbar; Änderungsprotokoll mit Kennzeichen „Eigenänderung“, sichtbar in der Verlaufsansicht des Mitglieds. Qualifikationen und Sonderaufgaben am eigenen Mitglied (und `Qualification.user` des eigenen Kontos) darf das Konto **nicht** anlegen, ändern oder löschen: Server lehnt mit 403 und Begründung ab; Oberfläche zeigt „Nachweise pflegt eine andere Person“. Eigene Änderungsanträge (falls über Portal gestellt) gibt eine andere Person frei.
- **Lösen:** durch Benutzerverwaltung jederzeit, durch das Konto nur als Antrag im Profil; Lösen beendet Selbstmeldungen nicht rückwirkend, bestehende Meldungen bleiben am Mitglied.
- **Elterndatensatz (Q4, offen):** gleiche Mechanik für `Parent`, dann „Meine Kinder“ im Verwaltungslayout.

## 5. Technisches Design

### 5.1 Neue Apps und Modelle

Neue Django-Apps `portal` und `participation`; Benachrichtigungsmodelle in `notifications`.

```text
users.CustomUser
  + account_kind: "staff" | "portal" (Standard "staff"; Portal-Konten erhalten nie Gruppen/Rollen)

portal.AccountLink                      # 1 Konto ↔ höchstens 1 Elterndatensatz und 1 Mitgliedsdatensatz
  user        OneToOne(CustomUser)        # Portal- ODER Verwaltendenkonto (PORTAL-04)
  parent      OneToOne(Parent, null)
  member      OneToOne(Member, null)
  status      pending | confirmed | rejected   # Portal-Einladung: confirmed bei Annahme; Verwaltende: pending bis Login-Bestätigung (E13)
  linked_by, linked_at, confirmed_at, rejected_at
  constraint: parent IS NOT NULL OR member IS NOT NULL
  # Wirkung (Rechte, Meldungen, Regelauswertung) nur bei status=confirmed

portal.Invitation
  parent | member (genau eins), email, token_hash, purpose="portal-invite"
  created_by, created_at, expires_at (7 Tage), accepted_at, revoked_at, accepted_user

portal.ParentAccessExtension
  parent, member, until (≤ 12 Monate nach 18. Geburtstag), reason, granted_by, created_at

portal.PortalPolicy                     # department NULL = Organisation
  department FK(null, unique)
  member_portal_mode: off | min_age | all, member_portal_min_age
  visibility: JSON {category: {parents: "visible"|"hidden", members: …}}
  ceiling: JSON (nur Organisationszeile) {category: {parents: "allowed"|"locked", …}}
  updated_by, updated_at, version

portal.ChangeRequest
  target_member FK(null) | target_parent FK(null)
  requested_by FK(CustomUser), status, version, created_at, updated_at
  fields: JSON [{field, old, new, decision: null|"applied"|"rejected", current_at_decision}]
  decided_by, decided_at, decision_note
  constraint: höchstens ein offener Antrag je Ziel

portal.ChangeLog                        # Übernahmeprotokoll (append-only)
  target, field, old, new, change_request, applied_by, applied_at

participation.ParticipationDefaults     # je Abteilung, department NULL = Organisation
  mode, registration_offset_h, cancellation_offset_h, waitlist_mode, urgent_notice_h

participation.SessionParticipation      # OneToOne(TrainingSession)
  mode: opt_out | opt_in | assignment
  portal_visible, public_note (Hinweis für Teilnehmende, Klartext ≤ 1000)
  registration_opens_at, registration_closes_at, cancellation_closes_at
  max_participants (null), min_participants (null), extra_places (null)
  waitlist_mode: auto | manual
  eligibility: JSON (Regelsprache v1)
  template_source FK(StaffingTemplate, null), revision
  assignment_published_at

participation.Slot
  session_participation FK, label, min, max, rule JSON, position (Reihenfolge)

participation.Registration
  session FK(TrainingSession), member FK(Member)
  state, slot FK(null), preferred_slot FK(null)
  reason_category, reason_note (≤ 200, Löschfrist D4)
  source, created_by FK(CustomUser), created_at, updated_at, state_changed_at
  conflict bool, conflict_reasons JSON, late bool, version
  unique(session, member); index(session, state, created_at)

participation.RegistrationEvent         # append-only Verlauf
  registration FK, actor FK(null), from_state, to_state, slot, at, via

participation.StaffingTemplate
  name, description, department FK(null), body JSON (Modus, Regeln, Slots, Zahlen), version, archived_at

notifications.InboxItem                 # ein Eintrag für das Team (E15)
  kind (z. B. cr_submitted, reg_cancelled), category (requests|registrations|staffing|accounts)
  item_type: task | notice
  department FK(null), object_type, object_id, title (ohne Freitexte), count, group_key (unique bei offenen Hinweisen)
  task_state: open | done (nur task), done_by FK(null), done_at, done_via (ui|email_action|auto)
  created_at, updated_at (Bündelung setzt nach oben), expires_at (180 Tage nach Erledigung)

notifications.InboxRecipient            # Empfängermenge + persönlicher Status
  item FK, user FK, read_at, hidden_at; unique(item, user)

notifications.NotificationPreference
  user, kind, email bool, push bool

notifications.PushSubscription
  + requests bool, + participation bool
```

Migrationen: rein additiv; `account_kind` Standard `staff` für alle bestehenden Konten. Keine Datenmigration bestehender `Attendance`-Werte. Neue Berechtigungen: `portal.review_changerequest`, `portal.invite_portal_account`, `portal.change_portalpolicy`, `participation.manage_participation`, `participation.change_staffingtemplate`. Rollenvorlagen-Erweiterung nur über ROLE-01-Vorlagenvergleich.

### 5.2 Sicherheitsarchitektur (zwingend vor jeder Portalfunktion)

1. **Globaler Ausschluss:** Neue Permission-Klasse `StaffAccountRequired` wird in `DEFAULT_PERMISSION_CLASSES` **vor** `CustomDefaultPermissions` eingetragen und verweigert Konten mit `account_kind="portal"`. Portal-Endpunkte setzen ausdrücklich `permission_classes = [PortalAccountRequired]`. Ausnahmen (für beide Kontoarten): Session/Login/Logout, Passwort ändern/zurücksetzen, MFA/Passkeys, Geräte/Sitzungen, Push-Abo, eigenes Profil. Zusätzlich für beide: `/actions/resolve/` und `/actions/execute/` (die ausgeführte Aktion prüft ihre eigenen Rechte). Der Eingang (`/notifications/inbox/`) bleibt Verwaltenden vorbehalten; Portalkonten erhalten Hinweise über `/portal/notifications/`.
2. **Audit vorhandener `IsAuthenticated`-Views:** Jede View, die `permission_classes` überschreibt (Liste in Abschnitt 3), wird geprüft und erhält `StaffAccountRequired` oder eine begründete Ausnahme. Ein Regressionstest iteriert über **alle** registrierten URL-Muster und prüft, dass ein Portalkonto außerhalb einer Allowlist 403 erhält (Test schlägt bei neuen, ungeschützten Endpunkten fehl).
3. **Objektbindung:** Portal-Querysets leiten sich nur aus `AccountLink` ab: `member` des Kontos und `Parent.children` des verknüpften Elterndatensatzes, gefiltert auf minderjährig oder gültige `ParentAccessExtension`. IDs aus Anfragen werden gegen diese Menge geprüft (404 statt 403 für fremde IDs).
4. **Eigene Serializer:** Portal-Serializer listen erlaubte Felder positiv (Allowlist je Kategorie), nie `exclude`. Notizen/Ereignisse/Anhänge existieren in Portal-Serializern nicht. Ein Test prüft Feldmengen gegen die Kategorietabelle.
5. **Rollen:** Rollenzuweisung (ROLE-02) verweigert Portalkonten; Umwandlung Portal → Betreuende nur durch Systemadministration mit Step-up und Protokoll.
6. **Rate-Limits:** Einladung annehmen und Meldungen (≤ 30 Schreibvorgänge/min je Konto), bestehender Login-Schutz gilt.
7. **CSRF/Sitzung:** unverändert Cookie-Sitzungen (SEC-07).
8. **Protokoll:** Einladung, Annahme, Entzug, Antragsentscheidung, Zuteilung und Betreuendenmeldung nach Frist erzeugen Einträge im bestehenden Sicherheits-/Änderungsprotokoll ohne Inhaltswerte personenbezogener Freitexte.

### 5.3 API (Entwurf, `/api/v1/…`)

Portal (nur `account_kind=portal` oder Betreuende mit verknüpftem Mitglied für `me`-Endpunkte):

| Methode | Pfad | Zweck |
| --- | --- | --- |
| GET | `/portal/me/` | Konto, verknüpfte Personen (ich + Kinder) mit effektiven Kategorien |
| GET | `/portal/people/{member_id}/` | Freigegebene Daten einer Person |
| GET/POST/PATCH/DELETE | `/portal/people/{id}/change-request/` | Offenen Antrag lesen, stellen, aktualisieren, zurückziehen (`kind=member|parent`) |
| GET | `/portal/sessions/?person={id}&from=&to=` | Meldefähige und kürzlich abgesagte Dienste mit Status, Fristen, freien Plätzen, Begründungen |
| GET | `/portal/sessions/{id}/?person={id}` | Detail inkl. `public_note`, Positionen (nur Name, frei/gesamt) |
| PUT | `/portal/sessions/{id}/registrations/{person_id}/` | Zielzustand setzen: `registered`, `cancelled`, `applied`, `withdrawn`; mit `slot`, `reason_category`, `reason_note`, `version` |
| POST | `/portal/absences/preview/` · `/portal/absences/` | Zeitraum-Abmeldung Vorschau/Ausführung |
| GET | `/portal/notifications/` | Portal-Hinweise |

Betreuende:

| Methode | Pfad | Zweck |
| --- | --- | --- |
| GET/PUT | `/training/sessions/{id}/participation/` | Konfiguration (Modus, Fristen, Zahlen, Regeln, Slots), Revision |
| POST | `/training/sessions/{id}/participation/preview/` | Live-Vorschau Zielgruppe/Erfüllung für ungespeicherte Regeln |
| GET | `/training/sessions/{id}/registrations/` | Alle Meldungen inkl. Eignung je Slot |
| PUT | `/training/sessions/{id}/registrations/{member_id}/` | Melden/abmelden für Person (Kennzeichnung `staff`, `late`) |
| POST | `/training/sessions/{id}/assignment/` | Zuteilungsentwurf speichern / veröffentlichen (`revision`) |
| GET/POST/PUT | `/participation/templates/` | Besetzungsvorlagen |
| GET/PUT | `/participation/defaults/{department_id|org}/` | Standards |
| GET | `/servicebook/services/{id}/registrations/` | Meldungsübersicht für Dienstbuch (lesend) |
| POST | `/servicebook/services/{id}/registrations/apply-excused/` | Ein-Klick-Übernahme (Vorschau mit `dry_run`) |
| GET/POST | `/portal/invitations/` · `/{id}/resend/` · `/{id}/revoke/` | Einladungen |
| GET/PUT | `/portal/policies/{department_id|org}/` | Freigaben |
| GET | `/portal/change-requests/?status=open` · POST `/{id}/decide/` | Prüf-Postfach, feldweise Entscheidung |
| GET | `/notifications/inbox/?type=&category=&department=&unread=` | Eingang (Aufgaben/Hinweise, nur eigene Empfängereinträge, Rechte erneut geprüft) |
| POST | `/notifications/inbox/{id}/read/` · `/inbox/read-bulk/` · `/inbox/{id}/done/` | Gelesen (persönlich), erledigt (Team) |
| GET | `/notifications/inbox/counts/` | Zähler für Navigation |
| POST | `/actions/resolve/` · `/actions/execute/` | Quick-Action prüfen (Modus, Vorschau, Zielroute) und ausführen; beide mit Sitzung und CSRF |
| POST | `/portal/account-links/` · `/{id}/confirm/` · `/{id}/reject/` · DELETE `/{id}/` | Verwaltendenkonto ↔ Mitglied verknüpfen, bestätigen, ablehnen, lösen |
| GET | `/portal/account-links/pending-for-me/` | Login-Zwischenschritt |
| GET/PUT | `/settings/email-templates/` (bestehend) | neue Typen samt Variablenkatalog und Vorschau |

Fehlerverträge: 409 mit `{"code":"stale","current":…}` bei Versionskonflikt; 422 mit `{"code":"deadline_passed"|"not_eligible"|"full"|"mode_forbidden","reasons":[…]}`.

### 5.4 Frontend

- **Portal-Layout** `PortalLayout.vue` (eigene, schlanke Navigation: Übersicht · Termine · Daten · Profil), mobil zuerst, Personenumschalter (Kinder/ich) als Chips. Routen unter `/portal/*` nur für `account_kind=portal`; Betreuende mit verknüpftem Mitglied erhalten „Meine Dienste“ im normalen Layout (dieselben Komponenten).
- **Komponenten:** `SessionCard` (Status-Badge mit Symbol+Text, Fristhinweis, Hauptaktion), `RegistrationSheet` (Bottom-Sheet: Grund, Position), `AbsenceRangeDialog`, `ChangeRequestForm` (Diff-Hinweis „wird nach Prüfung übernommen“), `RuleBuilder` + `RuleRow` + `RulePreview`, `SlotEditor`, `AssignmentBoard` (Drag via vorhandenem Planer-Muster, Tastaturalternative), `RegistrationsPanel` (Dienstbuch), `ChangeRequestReview`, `PortalPolicyMatrix`, `PortalAccessCard`, `InboxView` + `InboxItemCard` + `InboxBadge`, `ActionLandingView` (`/a/:token`, öffentliche Route), `AccountLinkDialog`, `AccountLinkConfirmStep` (Login-Zwischenschritt), mobiles Dienstbuch `ServicebookMobileList`, `AttendanceRow` (A/E/F ≥ 48 px), `RegistrationGroupList`, `ApplyExcusedSheet`.
- **Stores:** `portal.ts`, `participation.ts`; Fähigkeiten aus Session-API (Roadmap 3.6 „Effektive Fähigkeiten je Bereich“).
- **Design:** DES-01-Tokens; Status nie nur über Farbe; Touchflächen ≥ 44 px; Dunkelmodus; Breiten 360/390/768/1440.

### 5.5 Mockups (Design-Artifact)

| Artboard | Inhalt |
| --- | --- |
| Portal · Übersicht (mobil) | Personenumschalter, nächste Dienste mit Status, Fristen und Hauptaktion |
| Portal · Termin & Abmeldung (mobil) | Detail mit Plätzen/Warteliste, Bottom-Sheet Abmeldegrund |
| Portal · Daten & Änderungsantrag (mobil) | Freigegebene Kategorien, Antrag in Prüfung |
| Teilnahme-Konfigurator (Desktop) | Modus, Fristen, Regelbaukasten mit Live-Vorschau, Positionen mit Mindestbesetzung, Vorlage |
| Zuteilungsboard (Desktop) | Bewerbungen ↔ Positionen, Eignungsmarkierung, Mindestbesetzungsstatus |
| Dienstbuch · Meldungen (Desktop) | Meldestatus neben Anwesenheit, Ein-Klick-Übernahme |
| Änderungsanträge prüfen (Desktop) | Feldweiser Vergleich alt/neu/aktuell, Konfliktmarkierung |
| Einstellungen · Portal & Freigaben (Desktop) | Mitgliederportal-Schwelle, Freigabematrix Organisation/Abteilung, Fristenstandards |
| Dienstbuch mobil · Liste | Heute/Demnächst/Anwesenheit offen, eigener Meldestatus bei gebundenem Mitglied |
| Dienstbuch mobil · Meldungen | Zähler, Gruppen nach Status, Melden für Person |
| Dienstbuch mobil · Anwesenheit | Filterchips, A/E/F-Schaltflächen, Vorschläge, Speicherstatus |
| Dienstbuch mobil · Übernahme | Bottom-Sheet „Als entschuldigt übernehmen“ |
| Eingang (Desktop und mobil) | Aufgaben/Hinweise, Bündelung, Teamstatus, Aktionen |
| Quick Action nach Login (mobil) | Bestätigungsseite mit vorausgefüllter Aktion |
| E-Mails (Abmeldung kurzfristig, Änderungsantrag, Nachgerückt) | Gerenderte Standardvorlagen mit Quick-Action-Schaltflächen |
| Einstellungen · E-Mail-Vorlage bearbeiten | Bestehender Vorlageneditor mit neuen Typen, Variablen und Vorschau |
| Konto ↔ Mitglied verknüpfen | Dialog in der Benutzerverwaltung und Login-Bestätigung |

## 6. Ausführungsplan

### 6.1 Reihenfolge und Abhängigkeiten

```text
PORTAL-01 (Konten, Ausschluss, Einladung) ──┬─► PORTAL-02 (Freigaben, Selbstauskunft) ──► PORTAL-03 (Änderungsanträge)
                                            │
PART-03a (Regelsprache, Auswertung) ────────┼─► PART-01 (Teilnahme, Fristen, Portal-Termine) ──► PART-02 (Dienstbuch)
                                            │                         │
                                            │                         └─► PART-04 (Positionen, Warteliste, Zuteilung, Vorlagen)
NOTIF-01a (Inbox, Präferenzen) ─────────────┴─► von PORTAL-03, PART-01, PART-04 genutzt
PORTAL-01.1 (AccountLink) ──► PORTAL-04 (Verwaltende ↔ Mitglied) ──► „Meine Dienste“ in PART-01/PART-02
```

- `PORTAL-01.1`/`.2` (globaler Ausschluss + URL-Audit-Test) sind **Blocker** für jede weitere Portal-Auslieferung.
- `PART-03.1`–`.3` (Regelsprache, Auswertung, API) können parallel zu PORTAL-01 entstehen (keine gemeinsamen Dateien).
- Betreuendenseitige Teilnahme (PART-01 Backend + Konfigurator) ist auch ohne Portal nutzbar (Betreuende melden für Personen, verknüpfte Betreuendenkonten melden sich selbst).
- Abhängigkeiten zur Roadmap: SEC-07 (Sitzungen), SEC-05 (private Medien für Ausweisbild), SEC-08 (Formelschutz), ROLE-01/02 (Rechte, Vorlagenvergleich), CFG-01 (Konfigurationsquellen), TRAIN-01/03 (Revision, Serien, Vorlagenkopie), DES-01 (Tokens), UX-04 (Dienstbuch mobil).

### 6.2 Pakete und Teilschritte

Jeder Teilschritt ist ein eigener Commit nach EXEC-01 (Format `feat(PART-01.3): …`), inklusive Roadmap-Status und Journal.

**PORTAL-01: Portalkonten, Einladung und Zugriffsgrenzen**

| ID | Inhalt | Abnahme |
| --- | --- | --- |
| PORTAL-01.0 | Detailblock, Dateiverantwortung, offene Fragen Q2 klären | Roadmap aktualisiert |
| PORTAL-01.1 | `account_kind`, `AccountLink`, Migrationen, Admin nur lesend | Migration vorwärts/rückwärts, Modelltests |
| PORTAL-01.2 | `StaffAccountRequired` global, `PortalAccountRequired`, Allowlist; URL-Audit-Regressionstest über alle Routen | Test schlägt für ungeschützte Route fehl; alle Bestandstests grün |
| PORTAL-01.3 | Einladung (Modell, Token, E-Mail-Vorlage, Annahme über Passwort-festlegen-Seite, vorhandenes Konto verknüpfen) | Tests: Ablauf, Wiederverwendung, Widerruf, doppelte E-Mail, Rate-Limit |
| PORTAL-01.4 | Lebenszyklus: Sperren/Beenden mit Sitzungswiderruf; Elternzugriff endet mit 18 (Job, Vorwarnung, Verlängerung) | Zeitgesteuerte Tests (Schaltjahr 29.02., Zeitzone) |
| PORTAL-01.5 | Session-API `account_kind`, Router-Weiche, `PortalLayout`, Profil (Passwort, MFA optional, Geräte, Push) | Vitest, Browser: Login Elternteil → Portal, Betreuende unverändert |
| PORTAL-01.6 | Betreuenden-UI: Portalzugang-Karte an Eltern/Mitglied, Sammeleinladung | Browser, fehlende Rechte |
| PORTAL-01.7 | Paketabnahme (PostgreSQL, Rechte-Matrix Portal × alle Module, Browser 360/390/1440) | Prüfbericht im Journal |

**PORTAL-02: Freigaben und Selbstauskunft**

| ID | Inhalt | Abnahme |
| --- | --- | --- |
| PORTAL-02.0 | Detailblock | — |
| PORTAL-02.1 | `PortalPolicy` (Organisation/Abteilung, Obergrenze), Mitgliederportal-Schwelle, effektive Berechnung | Tests Obergrenze, Mehrfachabteilung (D2) |
| PORTAL-02.2 | Portal-Serializer mit Kategorie-Allowlist, `/portal/me/`, `/portal/people/{id}/`; Feldmengen-Test | Notizen/Ereignisse/Anhänge in keiner Antwort |
| PORTAL-02.3 | Einstellungen „Portal & Freigaben“ (Matrix, Schwelle) | Browser, Step-up nicht nötig, CFG-Quelle eindeutig |
| PORTAL-02.4 | Portal „Daten“-Ansicht (Kinder/ich) | Browser mobil |
| PORTAL-02.5 | Paketabnahme | — |

**PORTAL-03: Änderungsanträge**

| ID | Inhalt | Abnahme |
| --- | --- | --- |
| PORTAL-03.0 | Detailblock | — |
| PORTAL-03.1 | `ChangeRequest`, `ChangeLog`, Validierung, ein offener Antrag je Ziel | Tests inkl. HTML/Formel/Längen |
| PORTAL-03.2 | Portal-API und Formular | Vitest, Browser |
| PORTAL-03.3 | Prüf-Postfach: feldweise Entscheidung, Konflikt alt/aktuell, atomare Übernahme, Vier-Augen | Konkurrenztest PostgreSQL |
| PORTAL-03.4 | Benachrichtigungen (über NOTIF-01) | Tests ohne echten Versand |
| PORTAL-03.5 | Paketabnahme | — |

**PART-01: Teilnahme an geplanten Diensten**

| ID | Inhalt | Abnahme |
| --- | --- | --- |
| PART-01.0 | Detailblock, Q1 klären | — |
| PART-01.1 | `ParticipationDefaults`, `SessionParticipation`, `Registration`, `RegistrationEvent`; Statusmaschine als reine Funktion | Übergangstabelle vollständig getestet |
| PART-01.2 | Fristen- und Meldefähigkeitslogik (nur veröffentlicht + Zukunft; getrennte Fristen; Betreuende nach Frist; Einfrieren ab Beginn) | Grenzwerttests Sommerzeit |
| PART-01.3 | Betreuenden-API und Konfiguration „Teilnahme“-Tab im Planer (Modus, Fristen, Hinweis) | Browser |
| PART-01.4 | Portal: Termine je Person, An-/Abmelden, Grund, Zeitraum-Abmeldung | Browser mobil, Netzfehler, Frist abgelaufen |
| PART-01.5 | Serien und Terminänderungen (Kopie der Konfiguration je Termin, Benachrichtigung bei Verschiebung/Absage) | TRAIN-03-Serientests erweitert |
| PART-01.6 | Paketabnahme | — |

**PART-02: Dienstbuch-Integration**

| ID | Inhalt | Abnahme |
| --- | --- | --- |
| PART-02.0 | Detailblock | — |
| PART-02.1 | Meldungs-Endpunkt am Service, Zähler | Rechte: Portal 403 |
| PART-02.2 | Mobile Liste (Heute/Demnächst/Anwesenheit offen) und Dienst-Tabs; Abstimmung mit UX-04 | Browser 360/390 px, Touch |
| PART-02.3 | Mobile Meldungsansicht und Anwesenheitszeilen mit Meldestatus, gemeldete Gäste in Liste; Desktop als breite Variante | Browser mobil und 1440 px |
| PART-02.4 | Übernahme „entschuldigt“ als Bottom-Sheet mit Vorschau, nur leere Anwesenheit, bestehende Konfliktprüfung | Konkurrenztest mit paralleler Erfassung |
| PART-02.5 | Paketabnahme (mobil zuerst, Dunkelmodus, 200 % Zoom) | — |

**PART-03: Voraussetzungen und Konfigurator**

| ID | Inhalt | Abnahme |
| --- | --- | --- |
| PART-03.0 | Detailblock | — |
| PART-03.1 | Regelschema v1, Validierung, Klartext-Zusammenfassung | Schema-Tests, ungültige Regeln |
| PART-03.2 | Auswertung inkl. Kontoqualifikationen (E10), Begründungen, Abfrageeffizienz | ≤ konstante Abfragen je Vorschau |
| PART-03.3 | Vorschau-Endpunkt und Integration in Meldelogik (Sperre mit Begründung) | Tests |
| PART-03.4 | `RuleBuilder`-UI mit Live-Vorschau, Tastatur | Browser, a11y |
| PART-03.5 | Nachprüfung (Job + Ereignisse), Konfliktkennzeichnung, Aufgaben | Tests Ablauf/Entzug |
| PART-03.7 | Aufbauende Qualifikationen (E18): `QualificationType.includes` (M2M auf sich selbst, zyklenfrei validiert), Pflege in der Qualifikationsverwaltung, Auswertung/Vorschau/Zusammenfassung berücksichtigen die transitive Hülle; vor PART-04 umsetzen | Tests: Kette über drei Stufen, Zyklus abgelehnt, höhere Qualifikation abgelaufen, `has_none`, Abfragezahl konstant |
| PART-03.6 | Paketabnahme | — |

**PART-04: Plätze, Positionen, Warteliste, Zuteilung, Vorlagen**

| ID | Inhalt | Abnahme |
| --- | --- | --- |
| PART-04.0 | Detailblock, Q3 klären | — |
| PART-04.1 | `Slot`, Höchst-/Mindestzahlen, Mindestbesetzungsberechnung | Tests |
| PART-04.2 | Platzvergabe im Modus Anmeldung inkl. „beliebig“-Zuordnung und Warteliste je Position; Nachrücken auto/manuell | Konkurrenztest: 60 parallele Anmeldungen auf 3 Plätze → genau 3 |
| PART-04.3 | Slot-Editor im Konfigurator, Portalanzeige freie Plätze/Wartelistenposition | Browser |
| PART-04.4 | Modus Zuteilung: Bewerbungen, Board mit Drag-and-drop und Tastaturalternative, Entwurf/Veröffentlichen, Revision | Browser, 409-Konflikt |
| PART-04.5 | Besetzungsvorlagen (Speichern/Anwenden/Archivieren, Organisation/Abteilung), Übernahme in Übungsvorlagen/Serien | Kopie unabhängig |
| PART-04.6 | Paketabnahme | — |

**NOTIF-01: Aufgaben und Benachrichtigungen**

| ID | Inhalt | Abnahme |
| --- | --- | --- |
| NOTIF-01.0 | Detailblock | — |
| NOTIF-01.1 | `InboxItem`, `InboxRecipient`, `NotificationPreference`; Empfängerberechnung, Bündelung, Teamstatus, automatisches Erledigen | Tests inkl. Rechteentzug |
| NOTIF-01.2 | Eingang Desktop und mobil, Navigationszähler, Dashboard-Kachel | Browser 390/1440 px |
| NOTIF-01.3 | Neue `EmailTemplate`-Typen, Standardvorlagen (Anhang A), Variablenkatalog mit Beispieldaten, Pflichtlinks-Validierung, Vorschau im bestehenden Editor | Rendering-Tests, XSS-Testdaten |
| NOTIF-01.4 | Quick-Action-Links: Token, `/a/:token`, Login-Weiterleitung, resolve/execute, direkt/bestätigen (E12) | Tests: fremdes Konto, abgelaufen, entzogene Rechte, bereits erledigt, GET ohne Wirkung |
| NOTIF-01.5 | Idempotente Zustellung, Tageszusammenfassung, Push-Kategorien `requests`/`participation` ohne Namen; Teilnahmemitteilungen (E16) standardmäßig an, je Konto abschaltbar; statusabhängiger Abmeldelink (E17) | Kein Doppelversand; Test: jede Teilnahmemail enthält Abmelde- und Einstellungslink |
| NOTIF-01.6 | Paketabnahme | — |

**PORTAL-04: Verwaltendenkonto als Mitglied**

| ID | Inhalt | Abnahme |
| --- | --- | --- |
| PORTAL-04.0 | Detailblock, Q4 klären | — |
| PORTAL-04.1 | `AccountLink.status`, beidseitige Eindeutigkeit, Verknüpfen/Lösen-API mit Rechten | Tests: Doppelbindung, Portalkonto-Konflikt |
| PORTAL-04.2 | Login-Zwischenschritt Bestätigung/Ablehnung, Hinweise | Browser, MFA-/Passkey-Login |
| PORTAL-04.3 | „Meine Dienste“/„Meine Daten“ im Verwaltungslayout, Eigenänderungs-Protokoll, Vier-Augen-Sperre für eigene Qualifikationen/Sonderaufgaben | Tests 403 mit Begründung |
| PORTAL-04.4 | Qualifikationsdoppelungen anzeigen und zusammenführen; Dienstbuch „entweder Teilnehmende oder Betreuende“ | Tests, Auswertung zählt einmal |
| PORTAL-04.5 | Paketabnahme | — |

### 6.3 Prüfplan (zusätzlich zu Roadmap 5.4)

- **Rechte:** Portalkonto (Elternteil, Mitglied, beides) × jede Route; fremdes Kind per ID; Kind ab 18 ohne Verlängerung; Mitglied in Abteilung mit Portal „aus“; Betreuende ohne `review_changerequest`; Portalkonto mit manipuliertem `account_kind` im Request.
- **Daten:** Keine Notiz-, Ereignis-, Anhang-, Anwesenheits- oder Vorkommnisfelder in irgendeiner Portalantwort (Schlüsselsuche in JSON aller Portal-Endpunkte mit Testdaten, die Markerstrings enthalten).
- **Teilnahme:** Fristgrenzen (genau zur Frist, Sommerzeitwechsel), Modus-Wechsel mit bestehenden Meldungen (Opt-out → Opt-in: Abmeldungen bleiben, „erwartet“ wird „keine Rückmeldung“), Absage mit Meldungen, Zeitraum-Abmeldung über Serien.
- **Kapazität:** Parallele Anmeldungen (PostgreSQL), Nachrücken mit unpassender erster Person, „beliebig“-Zuordnung, Mindestbesetzung bei Abmeldung.
- **Regeln:** Ablauf am Diensttag, Kontoqualifikation verknüpfter Betreuender, fehlendes Geburtsdatum/Geschlecht, zwei Ebenen, ungültige Regeln.
- **Dienstbuch:** Übernahme nur leerer Werte, parallele Anwesenheitserfassung, keine Auswirkung ohne Klick.
- **UI:** 360/390/768/1440 px, Dunkelmodus, Tastatur (Board-Alternative), 200 % Zoom, Leer-/Fehler-/Rechtezustände.
- **Benachrichtigung:** Idempotenz, Abwahl, Sperrbildschirm ohne Namen.
- **Quick Actions:** Linkaufruf ohne Sitzung führt zum Login und zurück; fremdes Konto, abgelaufener/manipulierter Token, entzogenes Recht, gelöschtes Objekt, bereits erledigter Zustand; `GET` verändert nie Daten; `next` lehnt absolute und `//`-Pfade ab.
- **Vorlagen:** Datenbankvorlage überschreibt Standard, Zurücksetzen, fehlende Pflichtlinks abgelehnt, XSS-Testdaten in Namen/Titeln bleiben maskiert, keine Modellinstanzen im Kontext.
- **Eingang:** Bündelung, Teamstatus mit Name, persönlicher Gelesen-Status, automatisches Erledigen, Ausblenden nach Rechteentzug, Zähler.
- **Kontobindung:** ausstehend ohne Wirkung, Bestätigen/Ablehnen, Doppelbindung verhindert, eigene Qualifikation 403, Eigenänderung protokolliert, Person nie doppelt im Dienstbuch.
- **Mobil:** Dienstbuch vollständig bei 360 px ohne horizontales Scrollen, A/E/F mit Daumen erreichbar, Speicherstatus sichtbar.

### 6.4 Risiken

| Risiko | Gegenmaßnahme |
| --- | --- |
| Vorhandene Endpunkte mit `IsAuthenticated` geben Portalkonten Daten preis | PORTAL-01.2 als Blocker mit Routen-Audit-Test |
| Personenbezogene Gesundheitsangaben in Abmeldegründen | Kategorien, Kurztext mit Hinweis, Löschfrist (D4) |
| E-Mail-Flut bei vielen Meldungen | Sofort nur für kurzfristige/kritische Ereignisse, sonst Zusammenfassung; abwählbar |
| Gemeinsame E-Mail-Adressen (Familien) | Ein Konto je Adresse; ein Elterndatensatz kann mehrere Kinder führen; zweiter Elternteil braucht eigene Adresse |
| Qualifikationsdaten verteilt auf Konto und Mitglied | Einheitliche Auswertung (PART-03.2) und Verknüpfung (E10) |
| Seriengenerierung kopiert Teilnahmekonfiguration nicht | PART-01.5 erweitert TRAIN-03-Kopierlogik |
| Rechteerweiterung bestehender Rollen | Nur über ROLE-01-Vorlagenvergleich (D9) |
| Anpassbare Django-Templates erreichen Modellmethoden oder geben unmaskiertes HTML aus | Nur flacher Kontext, Autoescape, Sanitizer, Rendering-Tests mit XSS-Daten |
| Weitergeleitete E-Mails mit Quick Actions | Aktion nur für das adressierte, angemeldete Konto; Bestätigung bei Wirkung |
| Falsche Kontobindung | Bestätigung durch das Konto (E13), Lösen jederzeit, Protokoll |
| Eingang wird zur Massenablage | Bündelung, automatisches Erledigen, Aufbewahrungsfrist |

### 6.5 Übergabehinweise für umsetzende Agents

1. Roadmap und dieses Dokument lesen; Entscheidungen E1–E11 sind verbindlich, D1–D10 nur nach Rückfrage ändern, Q1–Q3 vor dem jeweiligen Paket klären.
2. Mit `PORTAL-01.0`–`.2` beginnen; parallel nur `PART-03.1`–`.3` (eigene Dateien).
3. Dateiverantwortung: `backend/portal/**`, `backend/participation/**`, `frontend/src/views/portal/**`, `frontend/src/components/participation/**` sind neu. Berührte Bestandsdateien (`settings.py` Permission-Klassen, `users/models.py`, `training/workflow.py`, `training/series.py`, `servicebook`-Views, `notifications/models.py`, Router) nur hunkweise stagen.
4. Demodaten (`seed_demo`) um fiktive Portalkonten, Meldungen, Positionen und eine Besetzungsvorlage „Brandsicherheitswache“ ergänzen (je Paket).
5. Mockups im Design-Artifact sind Zielbild, kein Pixelvertrag; Abweichungen zugunsten bestehender Komponenten (PrimeVue, DES-01) sind erwünscht und im Journal zu begründen.

## Anhang A: Standard-E-Mail-Vorlagen (Entwurf für NOTIF-01.3)

Die Texte sind Ausgangspunkte für `backend/templates/notifications/emails/`. Alle Vorlagen nutzen Django-Template-Syntax des bestehenden Systems, sind über „Einstellungen → E-Mail-Vorlagen“ überschreibbar und erhalten zusätzlich die gemeinsamen Variablen aus 4.9.3. Begriffe wie „Dienst“ kommen aus dem konfigurierbaren Vokabular (`terms.service`). Schaltflächen werden aus `actions` erzeugt, damit Layout und Quick Actions einheitlich bleiben:

```django
{% for a in actions %}<a href="{{ a.url }}" class="btn btn-{{ a.style }}">{{ a.label }}</a>{% endfor %}
```

| Typ | Layout | Betreff (Standard) | Typspezifische Variablen | Quick Actions (Modus) |
| --- | --- | --- | --- | --- |
| `portal_invite` | general | `Dein Zugang zu {{ org.name }}` | `invite.expires_at`, `invite.children` (Vornamen), `invite.kind` | Passwort festlegen (Einladungslink, kein Quick-Action-Token) |
| `account_link` | general | `Bitte bestätige die Verknüpfung mit deinem Mitgliedsdatensatz` | `link.member_name`, `link.linked_by` | Anmelden und bestätigen (bestätigen) |
| `cr_submitted` | important | `Änderungsantrag für {{ request.person_name }}` | `request.person_name`, `request.requested_by`, `request.fields` (`label`, `old`, `new`), `request.conflicts` | Prüfen (direkt öffnen), Alle übernehmen (bestätigen) |
| `cr_decided` | general | `Dein Änderungsantrag wurde bearbeitet` | `request.person_name`, `request.result` (übernommen/teilweise/abgelehnt), `request.fields`, `request.note` | Daten ansehen (direkt) |
| `reg_cancelled` | important | `Kurzfristige Abmeldung: {{ session.title }} am {{ session.date }}` | `session.title`, `session.date`, `session.time`, `cancellations` (`name`, `reason_category`, `at`), `counts`, `staffing.missing` | Meldungen ansehen (direkt), Als entschuldigt vormerken (bestätigen) |
| `reg_digest` | general | `Meldungen von heute ({{ counts.total }})` | `sessions` (je Dienst `title`, `date`, `counts`) | Eingang öffnen (direkt) |
| `slot_free_manual` | important | `Platz frei: {{ session.title }}` | `session.*`, `slot.label`, `waitlist` (Anzahl passender Wartender) | Platz besetzen (bestätigen) |
| `staffing_at_risk` | important | `Mindestbesetzung gefährdet: {{ session.title }}` | `session.*`, `staffing.missing` (`label`, `count`) | Board öffnen (direkt) |
| `waitlist_placed` | events | `Warteliste: {{ session.title }}` | `person.first_name`, `session.*`, `waitlist.position`, `waitlist.slot`, `waitlist.auto` (rückt automatisch nach) | Termin ansehen (direkt), Von der Warteliste abmelden (bestätigen) |
| `waitlist_promoted` | events | `{{ person.first_name }} ist nachgerückt: {{ session.title }}` | `person.first_name`, `session.*`, `session.public_note`, `deadlines.cancellation` | Termin ansehen (direkt), Abmelden (bestätigen) |
| `assign_published` | events | `{% if assignment.result == "assigned" %}Zugeteilt{% else %}Nicht berücksichtigt{% endif %}: {{ session.title }}` | `person.first_name`, `assignment.result` (`assigned`/`not_selected`), `assignment.slot`, `assignment.open_for_backfill`, `session.*` | Termin ansehen (direkt); Abmeldelink nach E17: Abmelden / Bewerbung zurückziehen / Keine weiteren Nachrichten (bestätigen) |
| `session_changed` | important | `Geändert: {{ session.title }}` bzw. `Abgesagt: …` | `session.*`, `change.kind` (verschoben/abgesagt/geändert), `change.old`, `change.new`, `person.first_name` | Termin ansehen (direkt), Abmelden (bestätigen, nur bei Verschiebung) |
| `eligibility_conflict` | important | `Voraussetzung nicht mehr erfüllt: {{ session.title }}` | `session.*`, `conflicts` (`name`, `reason`) | Meldungen ansehen (direkt) |
| `parent_access_end` | general | `Elternzugang für {{ person.first_name }} endet am {{ access.ends_at }}` | `person.first_name`, `access.ends_at`, `recipient.kind` | Ansehen (direkt); für Verwaltende: Mitglied einladen (bestätigen) |

Beispiel `reg_cancelled` (HTML-Teil innerhalb des Layouts):

```django
<p>Hallo {{ recipient.first_name }},</p>
<p>für <strong>{{ session.title }}</strong> am {{ session.date }}, {{ session.time }} {% if cancellations|length == 1 %}gibt es eine kurzfristige Abmeldung{% else %}gibt es {{ cancellations|length }} kurzfristige Abmeldungen{% endif %}:</p>
<ul>{% for c in cancellations %}<li>{{ c.name }} – {{ c.reason_category }} ({{ c.at }})</li>{% endfor %}</ul>
<p>Stand jetzt: {{ counts.expected }} erwartet, {{ counts.cancelled }} abgemeldet.{% if staffing.missing %} Es fehlt: {% for m in staffing.missing %}{{ m.count }}× {{ m.label }}{% if not forloop.last %}, {% endif %}{% endfor %}.{% endif %}</p>
{% for a in actions %}<a href="{{ a.url }}" class="btn btn-{{ a.style }}">{{ a.label }}</a> {% endfor %}
<p class="muted">Die Links funktionieren nach der Anmeldung mit deinem Konto. <a href="{{ links.preferences }}">Benachrichtigungen einstellen</a></p>
```

Textteil (`.txt`) jeweils mit denselben Informationen und den Aktionen als „Label: URL“-Zeilen.
