/**
 * Dynamic Item Form JavaScript
 * Erweitert Artikel-Formulare basierend auf Kategorie-Schema
 */

class DynamicItemForm {
    constructor() {
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadCategorySchema(); // Load schema on page load if category is already selected
    }

    setupEventListeners() {
        // Category change handler
        const categoryField = document.getElementById('id_category');
        if (categoryField) {
            categoryField.addEventListener('change', () => {
                this.loadCategorySchema();
            });
        }
    }

    async loadCategorySchema() {
        const categoryField = document.getElementById('id_category');
        const dynamicContainer = document.getElementById('dynamic-fields-container');
        const attributesField = document.getElementById('id_attributes');
        
        if (!categoryField || !dynamicContainer) {
            console.log('Required elements not found');
            return;
        }

        const categoryId = categoryField.value;
        
        // Clear existing dynamic fields
        dynamicContainer.innerHTML = '';
        
        if (!categoryId) {
            return;
        }

        try {
            const response = await fetch(`/inventory/api/categories/${categoryId}/schema/`);
            const data = await response.json();
            
            if (data.schema && Object.keys(data.schema).length > 0) {
                this.renderDynamicFields(data.schema, dynamicContainer, attributesField);
            }
        } catch (error) {
            console.error('Error loading category schema:', error);
        }
    }

    renderDynamicFields(schema, container, attributesField) {
        // Parse existing attributes if form is being edited
        let existingAttributes = {};
        if (attributesField && attributesField.value) {
            try {
                existingAttributes = JSON.parse(attributesField.value);
            } catch (e) {
                console.log('Could not parse existing attributes');
            }
        }

        // Create title
        const title = document.createElement('h6');
        title.className = 'mt-3 mb-3';
        title.textContent = 'Kategorie-spezifische Felder';
        container.appendChild(title);

        // Create dynamic fields based on schema
        Object.entries(schema).forEach(([fieldName, fieldType]) => {
            const fieldGroup = this.createDynamicField(fieldName, fieldType, existingAttributes[fieldName]);
            container.appendChild(fieldGroup);
        });

        // Update attributes field when dynamic fields change
        this.setupDynamicFieldHandlers(container, attributesField);
    }

    createDynamicField(fieldName, fieldType, existingValue = '') {
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
                
            case 'date':
                inputElement = document.createElement('input');
                inputElement.type = 'date';
                inputElement.value = existingValue || '';
                break;
                
            case 'boolean':
                inputElement = document.createElement('input');
                inputElement.type = 'checkbox';
                inputElement.checked = existingValue === true || existingValue === 'true';
                inputElement.className = 'form-check-input';
                label.className += ' form-check-label';
                break;
                
            case 'select':
                // For future enhancement: handle select options
                inputElement = document.createElement('select');
                inputElement.className = 'form-control';
                break;
                
            default: // string and others
                inputElement = document.createElement('input');
                inputElement.type = 'text';
                inputElement.value = existingValue || '';
                break;
        }

        if (inputElement.type !== 'checkbox') {
            inputElement.className = 'form-control';
        }
        
        inputElement.name = `dynamic_${fieldName}`;
        inputElement.id = `id_dynamic_${fieldName}`;
        inputElement.dataset.fieldName = fieldName;
        inputElement.dataset.fieldType = fieldType;

        fieldGroup.appendChild(inputElement);
        return fieldGroup;
    }

    setupDynamicFieldHandlers(container, attributesField) {
        const inputs = container.querySelectorAll('input, select');
        
        inputs.forEach(input => {
            input.addEventListener('change', () => {
                this.updateAttributesField(container, attributesField);
            });
            
            input.addEventListener('input', () => {
                this.updateAttributesField(container, attributesField);
            });
        });
    }

    updateAttributesField(container, attributesField) {
        if (!attributesField) return;

        const attributes = {};
        const inputs = container.querySelectorAll('input, select');
        
        inputs.forEach(input => {
            const fieldName = input.dataset.fieldName;
            const fieldType = input.dataset.fieldType;
            
            if (!fieldName) return;

            let value;
            
            if (input.type === 'checkbox') {
                value = input.checked;
            } else if (fieldType === 'number') {
                value = input.value ? parseFloat(input.value) : null;
            } else {
                value = input.value || null;
            }
            
            if (value !== null && value !== '') {
                attributes[fieldName] = value;
            }
        });

        attributesField.value = JSON.stringify(attributes);
    }

    formatFieldName(fieldName) {
        // Convert snake_case to Title Case
        return fieldName
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }
}

// Global function for backward compatibility with templates
function handleCategoryChange(categoryId) {
    const form = document.querySelector('.dynamic-item-form');
    if (form && form.dynamicItemForm) {
        form.dynamicItemForm.loadCategorySchema();
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    const dynamicContainer = document.getElementById('dynamic-fields-container');
    if (dynamicContainer) {
        console.log('Dynamic Item Form: Initializing...');
        const form = dynamicContainer.closest('form');
        if (form) {
            form.classList.add('dynamic-item-form');
            form.dynamicItemForm = new DynamicItemForm();
        }
    }
});
