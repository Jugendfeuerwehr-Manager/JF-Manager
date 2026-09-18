## Plan: Inventar und Bestellungen integrieren

TL;DR: Das Inventar wird zum führenden Artikelstamm. Bestellartikel referenzieren einen Inventar-Artikel; auswählbare Größen werden eindeutig auf Inventarvarianten aufgelöst. Ausleihen werden zu einem serverseitigen Mehrartikel-Vorgang erweitert. Verfügbare Positionen werden sofort ausgegeben, fehlende Positionen nur nach ausdrücklicher Bestätigung bestellt und als vorgemerkte Ausleihe geführt. Lieferungen buchen zunächst den Lagerzugang und markieren die Bestellposition als geliefert; die spätere Ausgabe bleibt ein separater, nachvollziehbarer Vorgang.

**Festgelegte Entscheidungen**
- Ein Inventar-Artikel ist die gemeinsame fachliche Identität für Lager und Bestellung.
- `OrderableItem` erhält eine Zuordnung zu `inventory.Item`; die Größe bleibt nicht unkontrolliert freier Text, sondern wird über eine eindeutige Variante bzw. Größen-/SKU-Zuordnung auf `ItemVariant` abgebildet.
- Eine vorgemerkte Ausleihe wird nicht automatisch bei Lieferung ausgegeben.
- Fehlende Positionen werden nur nach Bestätigung bestellt.
- Ersteinkleidung gilt für genau ein Mitglied pro Vorgang.
- Standardartikel werden am Inventar-Artikel gepflegt.
- Bei Teilbestand werden vorhandene Positionen sofort ausgegeben; fehlende Positionen werden bestellt und vorgemerkt.
- Die Lieferung einer Bestellung bucht den Eingang und setzt die Bestellposition auf geliefert. Die tatsächliche Ausgabe erfolgt danach separat.
- Die Einzel-Ausleihe bleibt als Rückfall- und schneller Einzelvorgang erhalten.

**Schritte**

### Phase 1: Datenmodell und Domänenvertrag
1. *Blockiert alle Folgephasen:* Fachliche Modellierung dokumentieren und mit vorhandenen Daten abgleichen: `OrderableItem`-Zuordnung zu `inventory.Item`, variantensichere Größenauflösung, Standardartikel-Flag, Bestellpositionen für automatisch erzeugte Fehlbestandsbestellungen sowie die Beziehung zwischen vorgemerkter Ausleihe und Bestellposition.
2. Inventarmodelle um das Standardartikel-Merkmal erweitern und eine eindeutige, validierte Mapping-Strategie für Bestellartikel und ItemVarianten einführen. Bestehende Artikel ohne Zuordnung bleiben zunächst manuell bestellbar, aber nicht automatisch lagerbuchbar.
3. Bestellmodelle um die Inventarverknüpfung, Liefer-/Zugangszustand und die für eine Vormerkung nötigen Referenzen erweitern. Statusänderungen dürfen nicht stillschweigend eine Ausgabe erzeugen.
4. Einen Inventory-Service als zentrale Mutationsgrenze entwerfen: Mitglieds-Lagerort serverseitig auflösen, Abteilungsrechte prüfen, Quellen bestimmen, Bestand mit Datenbanktransaktion und Zeilensperren reservieren/ändern und ein strukturiertes Ergebnis je Position liefern.
5. Die Semantik für vorgemerkte Fehlbestände festlegen: Status offen, bestellt, geliefert und ausgegeben; erlaubte Aktionen sind Bestellung anlegen, Lieferung buchen, spätere Ausgabe, Stornierung/Korrektur. Keine negative Lagerbestandsbuchung.

### Phase 2: Backend-APIs und Sicherheit
6. *Parallel nach Schritt 1-5:* Batch-Ausgabe-API implementieren, bevorzugt als eigener Inventory-Endpunkt oder Service-Aktion. Request: Mitglied, Positionen mit Item/Variant, Größe/Variante, Menge, Notiz, optional Ersteinkleidungskennung und Bestellbestätigung. Response: sofort ausgegebene, vorgemerkte, bestellte und fehlgeschlagene Positionen.
7. Die Batch-Ausgabe so implementieren, dass jede Position einzeln bewertet wird, aber konkurrierende Änderungen konsistent bleiben. Bei Teilbestand müssen erfolgreiche sofortige Ausgaben und vorgemerkte Fehlbestände in einem kontrollierten Vorgang sichtbar werden; doppelte oder widersprüchliche Positionen müssen validiert werden.
8. Endpoint für verfügbare Standardartikel eines einzelnen Mitglieds ergänzen. Er liefert Artikel, Varianten/Größen, Standardmenge und Bestandsstatus als serverseitig aufgelöste Vorschau, damit die Ersteinkleidung nicht aus einer zufälligen Frontend-Liste entsteht.
9. Bestell-/Liefer-API erweitern: aus bestätigten Fehlbestandspositionen eine Bestellung erzeugen, Bestellpositionen als geliefert markieren und dabei einen Lagerzugang an der gewählten Lagerquelle buchen. Lieferung darf nicht automatisch an das Mitglied ausgeben.
10. Berechtigungen und Department-Scoping analog zu den bestehenden Inventory- und Orders-Mixins umsetzen. Zentraler Bestand bleibt bei Schreibvorgängen eingeschränkt; fremde Mitglieder, Artikel, Bestellungen und Lagerorte dürfen nicht über IDs manipulierbar sein.
11. Backend-Tests ergänzen: Mapping und Größenauflösung, Standardartikel-Abfrage, batchweise Sofortausgabe, Teilbestand, fehlender Mitglieds-Lagerort, doppelte Positionen, unzureichender Bestand, Berechtigungen, Lieferzugang, vorgemerkte Ausleihe und konkurrierende Bestandsänderungen.

### Phase 3: Frontend-Verträge und State Ownership
12. *Nach Phase 2:* `frontend/src/types/inventory.ts` um Batch-Request, Vorschau, Positionsergebnis und Vormerkstatus erweitern. Bestands-/Variantentypen müssen die vom Backend gelieferte eindeutige Größenidentität abbilden.
13. `frontend/src/api/inventory.ts` um Standardartikel-Vorschau, Batch-Ausgabe und vorgemerkte Ausleihen erweitern. `frontend/src/api/orders.ts` erhält nur die Liefer-/Bestellmethoden, die der Backend-Vertrag tatsächlich bereitstellt.
14. `frontend/src/stores/inventory.ts` um die Orchestrierung der Batch-Ausgabe erweitern: Lade-/Fehlerstatus, Ergebnis je Position, Aktualisierung von Stocks, `memberLoans` und Mitgliedsausrüstung. Komponenten dürfen keine Einzeltransaktionen in Schleifen ausführen.
15. `frontend/src/stores/orders.ts` bzw. `orderableItems.ts` um gemeinsame Artikel-/Varianteninformationen und den Lieferstatus erweitern. Die bestehende Schnellbestellung bleibt nutzbar, verwendet aber bei zugeordneten Artikeln denselben Katalog.

### Phase 4: Mehrfachausgabe und Ersteinkleidung UX
16. *Parallel mit Phase 3:* Einen wiederverwendbaren Artikelzeilen-Editor aus den Mustern in `OrderFormView.vue` und `QuickOrderView.vue` herausarbeiten: Artikel, Größe/Variante, Menge, Bestandshinweis, Entfernen und Validierung.
17. `QuickLoanDialogV2.vue` um einen Mehrartikelmodus erweitern oder einen Geschwisterdialog für Batch-Ausgabe anlegen. Mitglied wird als Mitglied ausgewählt, nicht als scheinbare Storage-Location-ID. Der bestehende Einzelmodus bleibt erreichbar.
18. Im manuellen Mehrartikelmodus können mehrere Artikel/Varianten ergänzt werden. Der Dialog zeigt pro Zeile Bestand, sofortige Ausgabe oder Vormerkung und fragt nur bei fehlenden Positionen nach der Bestätigung für die Bestellung.
19. Ersteinkleidung als eigener Einstieg im Inventar-/Mitgliedskontext ergänzen: Mitglied wählen, serverseitig geladene Standardartikel anzeigen, Größe je Artikel wählen, Mengen bei Bedarf anpassen, Bestand und Bestellbedarf pro Zeile zeigen und gemischtes Ergebnis absenden.
20. Ergebnisdarstellung in `MemberLoansList.vue` und `MemberEquipmentTab.vue` erweitern: sofort ausgegebene Artikel, offene Vormerkungen und bestellte/gelieferte Positionen getrennt und verständlich anzeigen. Rückgabe-/Aussortierungsabläufe bleiben unverändert, außer eine Vormerkung benötigt explizite Stornierung.
21. Die bestehende Schnellbestellung so anpassen, dass zugeordnete Artikel dieselben Größen/Varianten wie das Inventar anbieten. Unzugeordnete Altbestellartikel werden sichtbar als manuell zu bearbeitende Ausnahme behandelt, nicht stillschweigend lagerfähig gemacht.

### Phase 5: Tests, Migration und Abnahme
22. Frontend-Store-Tests für Payload, gemischte Batch-Ergebnisse, Refreshes, Fehlerzustände und Bestellbestätigung ergänzen. Component-Tests prüfen Mitglieds-ID versus Lagerort-ID, mehrere Zeilen, Variantengrößen, Zurücksetzen bei Artikelwechsel, Duplikate, Menge, Ladezustand und Teilbestand.
23. Bestehende `OrderableItem`-Daten analysieren und eine sichere Zuordnungs-/Migrationsroutine vorbereiten. Nicht eindeutig zuordenbare Artikel werden protokolliert und müssen manuell nachgepflegt werden; keine automatische Zuordnung anhand ähnlich klingender Namen.
24. E2E-Test für Ersteinkleidung abdecken: Standardartikel laden, Größen wählen, verfügbaren und fehlenden Bestand gemischt absenden, Bestellbestätigung geben, Mitgliedsausrüstung prüfen und danach Lieferung sowie separate Ausgabe testen.
25. Fokussierte Backend-Tests und Frontend-Vitest zuerst ausführen. Danach die verpflichtenden Checks aus den Projektregeln: `cd frontend && npm run type-check`, `cd frontend && npm run lint`, `cd backend && pipenv run ruff check . && pipenv run ruff format --check .`.
26. Manuell regressionsprüfen: bisherige Einzel-Ausleihe, Rückgabe, Lagerbestand, Schnellbestellung, Bestellstatus, Lagerzugang und Mitgliedsausrüstung.

**Relevante Dateien**
- `backend/inventory/models/item.py` und `backend/inventory/models/variant.py` — Standardartikel und Variantengrundlage.
- `backend/inventory/models/stock.py` — `Transaction`, Bestandsmutation und Transaktionstypen; keine negative Bestandsbuchung für Vormerkungen.
- `backend/inventory/api/stock_transaction_viewsets.py` und `backend/inventory/api/location_viewsets.py` — bestehende API-Grenzen und Mitglieds-Lagerort-Auflösung.
- `backend/inventory/api/access.py` und `backend/departments/mixins.py` — Department-Scope und zentrale Datensätze.
- `backend/orders/models/orderable_item.py`, `order_item.py`, `order.py` — gemeinsamer Katalog, Größen-/Lieferdaten und Bestellbeziehung.
- `backend/orders/api/viewsets/order.py` — bestehendes `quick_create()` als Bestellmuster.
- `backend/orders/api/serializers/` — Validierung für Order, OrderItem und OrderableItem.
- `backend/jf_manager_backend/rest_urls.py` — Registrierung neuer API-Ressourcen/Aktionen.
- `frontend/src/components/inventory/molecules/QuickLoanDialogV2.vue` — bisheriger Einzel-Ausleihfluss.
- `frontend/src/stores/inventory.ts`, `frontend/src/api/inventory.ts`, `frontend/src/types/inventory.ts` — Frontend-Verträge und zentrale Inventarorchestrierung.
- `frontend/src/components/orders/QuickOrderView.vue` und `frontend/src/components/orders/OrderFormView.vue` — bestehende Mehrartikel-, Größen- und dynamische Zeilenmuster.
- `frontend/src/stores/orders.ts`, `frontend/src/stores/orderableItems.ts`, `frontend/src/api/orders.ts`, `frontend/src/types/orders.ts` — Bestellzustand und Katalogintegration.
- `frontend/src/components/inventory/organisms/MemberLoansList.vue` und `frontend/src/components/members/profile/MemberEquipmentTab.vue` — Ergebnis- und Statusanzeige.
- `frontend/src/views/InventoryView.vue`, `frontend/src/components/inventory/organisms/InventoryDashboard.vue`, `frontend/src/router/index.ts` — Einstiegspunkte; neue Route nur bei eigenständiger Verwaltung erforderlich.
- `backend/inventory/tests/`, `backend/orders/tests/`, `frontend/src/stores/__tests__/`, `frontend/tests/e2e/` — Testflächen.

**Verifikation**
1. Eine zugeordnete Bestellposition mit Größe löst exakt die erwartete Inventarvariante auf; eine nicht eindeutige oder fehlende Zuordnung wird abgelehnt bzw. als manuelle Ausnahme angezeigt.
2. Batch-Ausgabe mit vollständigem Bestand erzeugt für alle Positionen korrekte `LOAN`-Transaktionen und aktualisiert Lager sowie Mitgliedsausrüstung.
3. Batch-Ausgabe mit Teilbestand gibt verfügbare Positionen sofort aus und erzeugt für fehlende Positionen nur nach Bestätigung Bestellung plus Vormerkung.
4. Ohne Bestätigung entsteht keine Bestellung; ohne Bestand wird keine negative oder vorgetäuschte Lagerbuchung erzeugt.
5. Lieferung bucht den Eingang, aktualisiert den Bestellstatus und lässt die Vormerkung bestehen, bis eine separate Ausgabe erfolgt.
6. Department- und Rollenprüfungen verhindern fremde Artikel-, Mitglieds-, Lagerort- und Bestellzugriffe; zentrale Schreibregeln bleiben erhalten.
7. Standardartikel werden serverseitig geladen, genau einmal pro Ersteinkleidung angeboten und können vor dem Absenden in Größe und Menge angepasst werden.
8. Wiederholte Requests, konkurrierende Ausgaben und doppelte Zeilen führen nicht zu Überbestand oder doppelter Ausgabe.
9. Alle fokussierten Tests sowie die verpflichtenden Frontend- und Backend-Checks laufen erfolgreich; bestehende Einzel-Ausleihe und Rückgabe bleiben funktionsfähig.

**Scope-Grenzen**
- Enthalten: gemeinsame Artikel-/Variantenreferenzen, Standardartikel, Mehrfachausgabe, Ersteinkleidung, bestätigte Bestellungen bei Fehlbestand, Vormerkungen, Lieferzugang und separate spätere Ausgabe.
- Nicht enthalten: automatische Ersteinkleidung bei Mitgliederstellung, Mehrmitglieder-Sammelvorgänge, automatische Ausgabe bei Lieferung, vollständige Neuentwicklung des Bestellstatus-Workflows oder automatische Namens-basierte Datenmigration.


## Issues

- Bei eingang einer bestellung wird der bestand nicht gebucht. 
- Es wird keine Transaktion für eingegangen bestellung erzeugt: Der Bestand erhöht sich nicht. 
- Wenn ein Artikel an mehreren lagerorten, die nicht Personenbezogen sind verfügbar ist, muss auswählbar sein, von welchem lagerort ich ihn genommen habe.
- 