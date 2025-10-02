/**
 * Item Variants JavaScript
 * Verwaltet Artikel-Varianten für Größen und andere Attribute
 */

class ItemVariantManager {
    constructor() {
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadItemVariants();
    }

    setupEventListeners() {
        // Variant parent checkbox handler
        const isVariantParentField = document.getElementById('id_is_variant_parent');
        if (isVariantParentField) {
            isVariantParentField.addEventListener('change', () => {
                this.toggleVariantInterface();
            });
        }

        // Add variant button
        const addVariantBtn = document.getElementById('add-variant-btn');
        if (addVariantBtn) {
            addVariantBtn.addEventListener('click', () => {
                this.showVariantForm();
            });
        }
    }

    toggleVariantInterface() {
        const isVariantParent = document.getElementById('id_is_variant_parent').checked;
        const variantInterface = document.getElementById('variant-interface');
        
        if (variantInterface) {
            variantInterface.style.display = isVariantParent ? 'block' : 'none';
        }

        if (isVariantParent) {
            this.loadItemVariants();
        }
    }

    async loadItemVariants() {
        const itemId = this.getItemId();
        const variantsList = document.getElementById('variants-list');
        
        if (!itemId || !variantsList) {
            return;
        }

        try {
            const response = await fetch(`/inventory/api/items/${itemId}/variants/`);
            const data = await response.json();
            this.renderVariantsList(data.variants, variantsList);
        } catch (error) {
            console.error('Error loading variants:', error);
        }
    }

    renderVariantsList(variants, container) {
        if (!variants || variants.length === 0) {
            container.innerHTML = '<p class="text-muted">Keine Varianten vorhanden.</p>';
            return;
        }

        let html = '<div class="list-group">';
        
        variants.forEach(variant => {
            const attributesText = Object.entries(variant.variant_attributes)
                .map(([key, value]) => `${key}: ${value}`)
                .join(', ');
            
            html += `
                <div class="list-group-item d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${variant.sku || 'Ohne SKU'}</strong>
                        <br>
                        <small class="text-muted">${attributesText}</small>
                        <br>
                        <span class="badge badge-info">Bestand: ${variant.total_stock}</span>
                    </div>
                    <div class="btn-group" role="group">
                        <button type="button" class="btn btn-sm btn-outline-primary" 
                                onclick="editVariant(${variant.id})">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-danger" 
                                onclick="deleteVariant(${variant.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        container.innerHTML = html;
    }

    showVariantForm(variantId = null) {
        const modal = document.getElementById('variant-modal');
        const form = document.getElementById('variant-form');
        
        if (!modal || !form) {
            console.error('Variant modal or form not found');
            return;
        }

        // Reset form
        form.reset();
        
        if (variantId) {
            // Edit mode
            this.loadVariantForEdit(variantId);
        } else {
            // Create mode
            this.setupVariantFormFields();
        }

        // Show modal (assuming Bootstrap modal)
        if (window.bootstrap) {
            const modalInstance = new bootstrap.Modal(modal);
            modalInstance.show();
        } else {
            modal.style.display = 'block';
        }
    }

    async loadVariantForEdit(variantId) {
        try {
            const response = await fetch(`/inventory/api/variants/${variantId}/`);
            const variant = await response.json();
            
            // Populate form fields
            document.getElementById('variant-id').value = variant.id;
            document.getElementById('variant-sku').value = variant.sku || '';
            
            // Populate dynamic attributes
            this.populateVariantAttributes(variant.variant_attributes);
        } catch (error) {
            console.error('Error loading variant:', error);
        }
    }

    async setupVariantFormFields() {
        const itemId = this.getItemId();
        if (!itemId) return;

        try {
            // Get parent item's category schema to create variant fields
            const response = await fetch(`/inventory/api/items/${itemId}/`);
            const item = await response.json();
            
            if (item.category && item.category.schema) {
                this.createVariantAttributeFields(item.category.schema);
            }
        } catch (error) {
            console.error('Error setting up variant form:', error);
        }
    }

    createVariantAttributeFields(schema) {
        const container = document.getElementById('variant-attributes-container');
        if (!container) return;

        container.innerHTML = '';

        Object.entries(schema).forEach(([fieldName, fieldType]) => {
            const fieldGroup = this.createVariantAttributeField(fieldName, fieldType);
            container.appendChild(fieldGroup);
        });
    }

    createVariantAttributeField(fieldName, fieldType, existingValue = '') {
        const fieldGroup = document.createElement('div');
        fieldGroup.className = 'form-group mb-3';

        const label = document.createElement('label');
        label.textContent = this.formatFieldName(fieldName);
        label.className = 'form-label';
        fieldGroup.appendChild(label);

        let inputElement;

        switch (fieldType.toLowerCase()) {
            case 'number':
                inputElement = document.createElement('input');
                inputElement.type = 'number';
                inputElement.value = existingValue || '';
                break;
                
            default: // string and others
                inputElement = document.createElement('input');
                inputElement.type = 'text';
                inputElement.value = existingValue || '';
                break;
        }

        inputElement.className = 'form-control';
        inputElement.name = `variant_${fieldName}`;
        inputElement.id = `id_variant_${fieldName}`;
        inputElement.dataset.fieldName = fieldName;

        fieldGroup.appendChild(inputElement);
        return fieldGroup;
    }

    populateVariantAttributes(attributes) {
        Object.entries(attributes).forEach(([fieldName, value]) => {
            const input = document.getElementById(`id_variant_${fieldName}`);
            if (input) {
                input.value = value;
            }
        });
    }

    async saveVariant() {
        const form = document.getElementById('variant-form');
        const variantId = document.getElementById('variant-id').value;
        const itemId = this.getItemId();

        if (!form || !itemId) return;

        // Collect form data
        const formData = new FormData(form);
        const variantData = {
            parent_item: itemId,
            sku: formData.get('sku') || '',
            variant_attributes: this.collectVariantAttributes()
        };

        try {
            const url = variantId 
                ? `/inventory/api/variants/${variantId}/`
                : '/inventory/api/variants/';
            
            const method = variantId ? 'PUT' : 'POST';
            
            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(variantData)
            });

            if (response.ok) {
                this.hideVariantModal();
                this.loadItemVariants();
                this.showSuccessMessage('Variante gespeichert');
            } else {
                const error = await response.json();
                this.showErrorMessage('Fehler beim Speichern: ' + (error.detail || 'Unbekannter Fehler'));
            }
        } catch (error) {
            console.error('Error saving variant:', error);
            this.showErrorMessage('Fehler beim Speichern der Variante');
        }
    }

    collectVariantAttributes() {
        const container = document.getElementById('variant-attributes-container');
        if (!container) return {};

        const attributes = {};
        const inputs = container.querySelectorAll('input, select');
        
        inputs.forEach(input => {
            const fieldName = input.dataset.fieldName;
            if (fieldName && input.value) {
                attributes[fieldName] = input.value;
            }
        });

        return attributes;
    }

    async deleteVariant(variantId) {
        if (!confirm('Sind Sie sicher, dass Sie diese Variante löschen möchten?')) {
            return;
        }

        try {
            const response = await fetch(`/inventory/api/variants/${variantId}/`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (response.ok) {
                this.loadItemVariants();
                this.showSuccessMessage('Variante gelöscht');
            } else {
                this.showErrorMessage('Fehler beim Löschen der Variante');
            }
        } catch (error) {
            console.error('Error deleting variant:', error);
            this.showErrorMessage('Fehler beim Löschen der Variante');
        }
    }

    getItemId() {
        // Try to get item ID from URL or hidden field
        const pathParts = window.location.pathname.split('/');
        const itemIndex = pathParts.indexOf('items');
        if (itemIndex !== -1 && pathParts[itemIndex + 1]) {
            return pathParts[itemIndex + 1];
        }
        
        // Try hidden field
        const hiddenField = document.getElementById('item-id');
        if (hiddenField) {
            return hiddenField.value;
        }
        
        return null;
    }

    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    hideVariantModal() {
        const modal = document.getElementById('variant-modal');
        if (modal) {
            if (window.bootstrap) {
                const modalInstance = bootstrap.Modal.getInstance(modal);
                if (modalInstance) {
                    modalInstance.hide();
                }
            } else {
                modal.style.display = 'none';
            }
        }
    }

    showSuccessMessage(message) {
        // Simple alert for now - can be enhanced with toast notifications
        alert(message);
    }

    showErrorMessage(message) {
        // Simple alert for now - can be enhanced with toast notifications
        alert(message);
    }

    formatFieldName(fieldName) {
        return fieldName
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }
}

// Global functions for template access
function editVariant(variantId) {
    if (window.itemVariantManager) {
        window.itemVariantManager.showVariantForm(variantId);
    }
}

function deleteVariant(variantId) {
    if (window.itemVariantManager) {
        window.itemVariantManager.deleteVariant(variantId);
    }
}

function saveVariant() {
    if (window.itemVariantManager) {
        window.itemVariantManager.saveVariant();
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    const isVariantParentField = document.getElementById('id_is_variant_parent');
    if (isVariantParentField) {
        console.log('Item Variant Manager: Initializing...');
        window.itemVariantManager = new ItemVariantManager();
    }
});
