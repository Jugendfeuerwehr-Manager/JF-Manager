/**
 * Smart Transaction Form JavaScript
 * Bietet Live-Suche für Artikel und Lagerorte sowie intelligente Formularlogik
 */

class SmartTransactionForm {
    constructor() {
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupSearchFields();
        this.setupTransactionTypeLogic();
        this.updateFormVisibility();
    }

    setupEventListeners() {
        // Transaction Type Change
        const transactionTypeField = document.getElementById('id_transaction_type');
        if (transactionTypeField) {
            transactionTypeField.addEventListener('change', () => {
                this.updateFormVisibility();
                this.clearStockInfo();
            });
        }

        // Item/Location Changes für Stock Info
        const itemField = document.getElementById('id_item');
        const sourceField = document.getElementById('id_source');
        
        if (itemField) {
            itemField.addEventListener('change', () => this.updateStockInfo());
        }
        
        if (sourceField) {
            sourceField.addEventListener('change', () => this.updateStockInfo());
        }
    }

    setupSearchFields() {
        // Item Search
        this.setupItemSearch();
        
        // Location Search
        this.setupLocationSearch();
    }

    setupItemSearch() {
        const searchField = document.getElementById('id_search_item');
        const itemSelect = document.getElementById('id_item');
        const variantSelect = document.getElementById('id_item_variant');
        
        if (!searchField || !itemSelect || !variantSelect) return;

        let searchTimeout;
        
        searchField.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                this.searchItems(e.target.value);
            }, 300);
        });

        // Change handlers für Bestand
        itemSelect.addEventListener('change', () => {
            // Wenn Item gewählt wurde, Variante zurücksetzen
            if (itemSelect.value) {
                variantSelect.value = '';
            }
            this.updateStockInfo();
        });
        variantSelect.addEventListener('change', () => {
            if (variantSelect.value) {
                itemSelect.value = '';
            }
            this.updateStockInfo();
        });
    }

    setupLocationSearch() {
        // Source Location Search
        this.setupSingleLocationSearch('search_source', 'source');
        
        // Target Location Search
        this.setupSingleLocationSearch('search_target', 'target');
    }

    setupSingleLocationSearch(searchFieldId, selectFieldId) {
        const searchField = document.getElementById(`id_${searchFieldId}`);
        const selectField = document.getElementById(`id_${selectFieldId}`);
        
        if (!searchField || !selectField) return;

        let searchTimeout;
        
        searchField.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                this.searchLocations(e.target.value, selectFieldId);
            }, 300);
        });

        // Wenn aus Select gewählt wird, Search-Feld aktualisieren
        selectField.addEventListener('change', (e) => {
            const selectedOption = e.target.options[e.target.selectedIndex];
            if (selectedOption.value) {
                searchField.value = selectedOption.text;
                if (selectFieldId === 'source') {
                    this.updateStockInfo();
                }
            } else {
                searchField.value = '';
            }
        });
    }

    async searchItems(query) {
        if (query.length < 2) return;

        const sourceLocationId = document.getElementById('id_source')?.value;
        const params = new URLSearchParams({ q: query });
        try {
            // New unified DRF search: items then variants
            const itemResp = await fetch(`/api/v1/inventory/items/search/?${params}`);
            const itemData = await itemResp.json();
            const variantResp = await fetch(`/api/v1/inventory/variants/?search=${encodeURIComponent(query)}`);
            const variantData = await variantResp.json();
            // Normalize to former shape
            const combined = [];
            (itemData.results || itemData.items || []).forEach(i => {
                combined.push({
                    id: i.id,
                    name: i.name,
                    category: i.category_name || '',
                    display_name: i.name + (i.category_name ? ` (${i.category_name})` : ''),
                    type: 'item',
                    stock: { total_quantity: i.total_stock }
                });
            });
            (variantData.results || variantData) .forEach(v => {
                combined.push({
                    id: `variant_${v.id}`,
                    variant_id: v.id,
                    name: v.parent_item_name,
                    category: v.category_name || '',
                    display_name: v.parent_item_name + (v.sku ? ` [${v.sku}]` : ''),
                    type: 'variant',
                    stock: { total_quantity: v.total_stock }
                });
            });
            this.updateItemOptions(combined);
        } catch (error) {
            console.error('Error searching items:', error);
        }
    }

    async searchLocations(query, fieldType) {
        if (query.length < 2) return;

        try {
            const resp = await fetch(`/api/v1/inventory/locations/?search=${encodeURIComponent(query)}`);
            const data = await resp.json();
            // DRF pagination may wrap results
            const results = data.results || data;
            const normalized = results.map(l => ({
                id: l.id,
                full_path: l.full_path || l.name,
                is_member: l.is_member,
                stock_info: null,
            }));
            this.updateLocationOptions(normalized, fieldType);
        } catch (error) {
            console.error('Error searching locations:', error);
        }
    }

    updateItemOptions(items) {
        const itemSelect = document.getElementById('id_item');
        const variantSelect = document.getElementById('id_item_variant');
        if (!itemSelect || !variantSelect) return;

        const currentItem = itemSelect.value;
        const currentVariant = variantSelect.value;

        itemSelect.innerHTML = '<option value="">--- Artikel wählen ---</option>';
        variantSelect.innerHTML = '<option value="">--- Variante wählen ---</option>';

        items.forEach(entry => {
            if (entry.type === 'variant') {
                const opt = document.createElement('option');
                opt.value = entry.variant_id;
                opt.textContent = entry.display_name;
                if (entry.stock) opt.dataset.stock = JSON.stringify(entry.stock);
                variantSelect.appendChild(opt);
            } else {
                const opt = document.createElement('option');
                opt.value = entry.id;
                opt.textContent = entry.display_name;
                if (entry.stock) opt.dataset.stock = JSON.stringify(entry.stock);
                itemSelect.appendChild(opt);
            }
        });

        if (currentItem) itemSelect.value = currentItem;
        if (currentVariant) variantSelect.value = currentVariant;
    }

    updateLocationOptions(locations, fieldType) {
        const selectField = document.getElementById(`id_${fieldType}`);
        if (!selectField) return;

        // Aktuelle Auswahl merken
        const currentValue = selectField.value;
        
        // Optionen löschen (außer der ersten leeren Option)
        selectField.innerHTML = '<option value="">--- Lagerort wählen ---</option>';
        
        // Neue Optionen hinzufügen
        locations.forEach(location => {
            const option = document.createElement('option');
            option.value = location.id;
            option.textContent = location.full_path;
            
            // Zusätzliche Infos als data-attributes
            option.dataset.isMember = location.is_member;
            option.dataset.stockInfo = JSON.stringify(location.stock_info);
            
            selectField.appendChild(option);
        });

        // Vorherige Auswahl wiederherstellen falls möglich
        if (currentValue) {
            selectField.value = currentValue;
        }
    }

    setupTransactionTypeLogic() {
        const transactionType = document.getElementById('id_transaction_type');
        if (!transactionType) return;

        // Initial setup
        this.updateFormVisibility();
    }

    updateFormVisibility() {
        const transactionType = document.getElementById('id_transaction_type')?.value;
        const sourceSection = document.getElementById('source-section');
        const targetSection = document.getElementById('target-section');
        
        if (!sourceSection || !targetSection) return;

        // Standardmäßig beide verstecken
        sourceSection.style.display = 'none';
        targetSection.style.display = 'none';

        // Je nach Transaktionstyp entsprechende Felder anzeigen
        switch (transactionType) {
            case 'IN':      // Eingang - nur Ziel
            case 'RETURN':  // Rückgabe - nur Ziel
                targetSection.style.display = 'block';
                this.setFieldRequired('target', true);
                this.setFieldRequired('source', false);
                break;
                
            case 'OUT':     // Ausgang - nur Quelle
            case 'DISCARD': // Aussortierung - nur Quelle
                sourceSection.style.display = 'block';
                this.setFieldRequired('source', true);
                this.setFieldRequired('target', false);
                break;
                
            case 'MOVE':    // Umlagerung - beide
            case 'LOAN':    // Ausleihe - beide
                sourceSection.style.display = 'block';
                targetSection.style.display = 'block';
                this.setFieldRequired('source', true);
                this.setFieldRequired('target', true);
                break;
                
            default:
                // Beide anzeigen falls unbekannter Typ
                sourceSection.style.display = 'block';
                targetSection.style.display = 'block';
                break;
        }
    }

    setFieldRequired(fieldName, required) {
        const field = document.getElementById(`id_${fieldName}`);
        const searchField = document.getElementById(`id_search_${fieldName}`);
        
        if (field) {
            field.required = required;
        }
        if (searchField) {
            searchField.required = required;
        }
    }

    async updateStockInfo() {
        const itemField = document.getElementById('id_item');
        const variantField = document.getElementById('id_item_variant');
        const sourceId = document.getElementById('id_source')?.value;
        const stockInfoDiv = document.getElementById('stock-info');
        
        if (!stockInfoDiv || (!itemField && !variantField)) return;

        const itemId = itemField.value;
        const variantId = variantField.value;
        if (!itemId && !variantId) {
            stockInfoDiv.style.display = 'none';
            return;
        }

        const params = new URLSearchParams();
        if (variantId) params.append('variant_id', variantId);
        if (itemId) params.append('item_id', itemId);
        
        if (sourceId) {
            params.append('location_id', sourceId);
        }

        try {
            let data = null;
            if (variantId) {
                const resp = await fetch(`/api/v1/inventory/variants/${variantId}/stock/`);
                data = await resp.json();
                if (data.rows) {
                    const total = data.total;
                    data = { stock: { item_name: 'Variante', total_quantity: total, locations: data.rows.map(r => ({ location_name: r.location_name, quantity: r.quantity })) } };
                }
            } else if (itemId) {
                const resp = await fetch(`/api/v1/inventory/items/${itemId}/stock/`);
                data = await resp.json();
                if (data.rows) {
                    const total = data.total;
                    data = { stock: { item_name: 'Artikel', total_quantity: total, locations: data.rows.map(r => ({ location_name: r.location_name, quantity: r.quantity })) } };
                }
            }
            if (data && data.stock) this.displayStockInfo(data.stock, stockInfoDiv);
        } catch (error) {
            console.error('Error fetching stock info:', error);
            stockInfoDiv.style.display = 'none';
        }
    }

    displayStockInfo(stock, container) {
        let html = '';
        
        if (stock.location_name) {
            // Bestand an spezifischem Lagerort
            html = `
                <i class="fas fa-info-circle"></i>
                <strong>Bestand bei "${stock.location_name}":</strong> 
                ${stock.quantity} Stück
                ${stock.has_stock ? '' : ' <span class="text-warning">(Nicht verfügbar)</span>'}
            `;
        } else if (stock.locations) {
            // Bestand über alle Lagerorte
            html = `
                <i class="fas fa-info-circle"></i>
                <strong>Gesamtbestand für "${stock.item_name}":</strong> ${stock.total_quantity} Stück
            `;
            
            if (stock.locations.length > 0) {
                html += '<br><small>Verfügbar in: ';
                html += stock.locations.map(loc => 
                    `${loc.location_name} (${loc.quantity})`
                ).join(', ');
                html += '</small>';
            }
        }
        
        if (html) {
            container.innerHTML = html;
            container.style.display = 'block';
        } else {
            container.style.display = 'none';
        }
    }

    clearStockInfo() {
        const stockInfoDiv = document.getElementById('stock-info');
        if (stockInfoDiv) {
            stockInfoDiv.style.display = 'none';
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Smart Transaction Form: DOM loaded');
    const transactionTypeField = document.getElementById('id_transaction_type');
    if (transactionTypeField) {
        console.log('Smart Transaction Form: Initializing...');
        new SmartTransactionForm();
    } else {
        console.log('Smart Transaction Form: Transaction type field not found');
    }
});
