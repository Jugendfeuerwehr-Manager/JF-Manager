<template>
  <Dialog
    v-model:visible="visible"
    :header="isEdit ? 'Artikel bearbeiten' : 'Neuer Artikel'"
    :style="{ width: '600px' }"
    modal
    :closable="!loading"
  >
    <div class="item-form">
      <div class="field">
        <label for="name">Name *</label>
        <InputText id="name" v-model="form.name" class="w-full" placeholder="Artikelname" />
      </div>

      <div class="field">
        <label for="category">Kategorie *</label>
        <Dropdown
          id="category"
          v-model="form.category"
          :options="inventoryStore.categoryOptions"
          option-label="label"
          option-value="value"
          placeholder="Kategorie auswählen"
          class="w-full"
        />
      </div>

      <div class="field">
        <label for="baseUnit">Einheit</label>
        <InputText id="baseUnit" v-model="form.base_unit" class="w-full" placeholder="z.B. Stück, Paar" />
      </div>

      <div class="field-row">
        <div class="field">
          <label for="identifier1">Inventarnummer (Hand)</label>
          <InputText id="identifier1" v-model="form.identifier1" placeholder="Manuelle Nr." />
        </div>
        <div class="field">
          <label for="identifier2">Inventarnummer (Barcode)</label>
          <InputText id="identifier2" v-model="form.identifier2" placeholder="Barcode Nr." />
        </div>
      </div>

      <div class="field">
        <div class="flex align-items-center gap-2">
          <Checkbox v-model="form.is_variant_parent" input-id="hasVariants" binary />
          <label for="hasVariants">Hat Varianten (z.B. verschiedene Größen)</label>
        </div>
      </div>

      <div class="field">
        <div class="flex align-items-center gap-2">
          <Checkbox v-model="form.is_standard_item" input-id="isStandardItem" binary />
          <label for="isStandardItem">Standardartikel (Teil der Ersteinkleidung)</label>
        </div>
      </div>

      <!-- Variant Management (only if editing an item with variants) -->
      <div v-if="form.is_variant_parent && isEdit" class="variants-section">
        <Divider />
        <div class="variants-header">
          <h4>Varianten</h4>
          <div class="variants-header-actions">
            <Button
              label="Größen generieren"
              icon="pi pi-th-large"
              size="small"
              :outlined="!showGenerator"
              @click="toggleGenerator"
            />
            <Button
              label="Variante hinzufügen"
              icon="pi pi-plus"
              size="small"
              outlined
              @click="openVariantDialog(null)"
            />
          </div>
        </div>
        <div v-if="showGenerator" class="generator">
          <div class="field-row">
            <div class="field">
              <label for="sizePreset">Größenreihe</label>
              <Dropdown
                id="sizePreset"
                v-model="generator.presetKey"
                :options="SIZE_PRESETS"
                option-label="label"
                option-value="key"
                placeholder="Vorlage wählen"
                class="w-full"
                @change="applyPreset"
              />
            </div>
            <div class="field">
              <label for="sizeAttribute">Attribut</label>
              <InputText id="sizeAttribute" v-model="generator.attribute" placeholder="Größe" />
            </div>
          </div>
          <div v-if="generatorCandidates.length" class="field">
            <div class="generator-values-header">
              <label>Werte</label>
              <div>
                <Button label="Alle" size="small" text @click="selectAllCandidates" />
                <Button label="Keine" size="small" text @click="generator.selected = []" />
              </div>
            </div>
            <div class="size-chips">
              <button
                v-for="value in generatorCandidates"
                :key="value"
                type="button"
                class="size-chip"
                :class="{ selected: generator.selected.includes(value), existing: isExistingValue(value) }"
                :disabled="isExistingValue(value)"
                :title="isExistingValue(value) ? 'Variante existiert bereits' : undefined"
                :aria-pressed="generator.selected.includes(value)"
                @click="toggleCandidate(value)"
              >
                {{ value }}
              </button>
            </div>
          </div>
          <div class="field">
            <label for="customSizes">Weitere Werte</label>
            <InputText
              id="customSizes"
              v-model="generator.custom"
              placeholder="z.B. XS, 4XL (durch Komma getrennt)"
              @keydown.enter.prevent="addCustomValues"
              @blur="addCustomValues"
            />
          </div>
          <div class="generator-footer">
            <small>{{ newGeneratorValues.length }} neue Varianten</small>
            <Button
              :label="`${newGeneratorValues.length} Varianten anlegen`"
              icon="pi pi-check"
              size="small"
              :loading="variantLoading"
              :disabled="!newGeneratorValues.length || !generator.attribute.trim()"
              @click="generateVariants"
            />
          </div>
        </div>
        <div v-if="currentItem?.variants?.length" class="variants-list">
          <div v-for="variant in currentItem.variants" :key="variant.id" class="variant-item">
            <div class="variant-info">
              <span class="variant-name">{{ formatVariantAttributes(variant.variant_attributes) }}</span>
              <span v-if="variant.sku" class="variant-sku">SKU: {{ variant.sku }}</span>
            </div>
            <div class="variant-actions">
              <Tag :value="`${variant.total_stock} Stk.`" severity="secondary" />
              <Button
                icon="pi pi-pencil"
                size="small"
                text
                rounded
                severity="secondary"
                title="Bearbeiten"
                @click="openVariantDialog(variant)"
              />
              <Button
                icon="pi pi-trash"
                size="small"
                text
                rounded
                severity="danger"
                title="Löschen"
                @click="confirmDeleteVariant(variant)"
              />
            </div>
          </div>
        </div>
        <div v-else class="empty-variants">
          <small>Noch keine Varianten vorhanden</small>
        </div>
      </div>
    </div>

    <template #footer>
      <Button label="Abbrechen" severity="secondary" text @click="closeDialog" :disabled="loading" />
      <Button
        :label="isEdit ? 'Speichern' : 'Erstellen'"
        icon="pi pi-check"
        :loading="loading"
        @click="submit"
        :disabled="!isValid"
      />
    </template>
  </Dialog>

  <!-- Variant Dialog -->
  <Dialog
    v-model:visible="showVariantDialog"
    :header="editingVariant ? 'Variante bearbeiten' : 'Neue Variante'"
    :style="{ width: '450px' }"
    modal
  >
    <div class="variant-form">
      <div class="field">
        <label>Attribute (z.B. Größe, Farbe)</label>
        <div class="attributes-list">
          <div v-for="(value, key) in variantForm.attributes" :key="key" class="attribute-row">
            <InputText :model-value="String(key)" disabled placeholder="Attribut" />
            <InputText v-model="variantForm.attributes[key]" placeholder="Wert" />
            <Button 
              icon="pi pi-times" 
              size="small" 
              text 
              rounded 
              severity="danger"
              @click="removeAttribute(String(key))" 
            />
          </div>
        </div>
        <div class="add-attribute-row">
          <InputText v-model="newAttributeKey" placeholder="Neues Attribut (z.B. Größe)" />
          <InputText v-model="newAttributeValue" placeholder="Wert (z.B. 164)" />
          <Button 
            icon="pi pi-plus" 
            size="small" 
            @click="addAttribute" 
            :disabled="!newAttributeKey || !newAttributeValue"
          />
        </div>
      </div>
      <div class="field">
        <label for="sku">SKU/Artikelnummer</label>
        <InputText id="sku" v-model="variantForm.sku" class="w-full" placeholder="Optional" />
      </div>
    </div>
    <template #footer>
      <Button label="Abbrechen" severity="secondary" text @click="showVariantDialog = false" />
      <Button
        :label="editingVariant ? 'Speichern' : 'Hinzufügen'"
        icon="pi pi-check"
        :loading="variantLoading"
        @click="saveVariant"
        :disabled="Object.keys(variantForm.attributes).length === 0"
      />
    </template>
  </Dialog>

  <!-- Confirm Delete Variant -->
  <ConfirmDialog group="variant" />
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Dropdown from 'primevue/dropdown'
import Checkbox from 'primevue/checkbox'
import Divider from 'primevue/divider'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import ConfirmDialog from 'primevue/confirmdialog'
import { useConfirm } from 'primevue/useconfirm'
import { useInventoryStore } from '@/stores/inventory'
import { useToast } from 'primevue/usetoast'
import type { Item, ItemCreate, ItemUpdate, ItemVariant } from '@/types/inventory'
import { SIZE_PRESETS, parseSizeValues } from '@/utils/sizePresets'
import { getApiErrorMessage } from '@/utils/apiError'

interface Props {
  modelValue: boolean
  item?: Item | null
}

const props = withDefaults(defineProps<Props>(), {
  item: null
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  success: [item: Item]
}>()

const inventoryStore = useInventoryStore()
const toast = useToast()
const confirm = useConfirm()

const loading = ref(false)
const variantLoading = ref(false)
const showVariantDialog = ref(false)
const editingVariant = ref<ItemVariant | null>(null)
const newAttributeKey = ref('')
const newAttributeValue = ref('')

const form = ref<ItemCreate & ItemUpdate>({
  name: '',
  category: 0,
  base_unit: 'Stück',
  attributes: null,
  is_variant_parent: false,
  is_standard_item: false,
  size: '',
  identifier1: '',
  identifier2: ''
})

const variantForm = ref({
  attributes: {} as Record<string, string>,
  sku: ''
})

// Local copy so the variant list reflects changes made inside the dialog.
const currentItem = ref<Item | null>(null)

const showGenerator = ref(false)
const generator = ref({
  presetKey: null as string | null,
  attribute: 'Größe',
  candidates: [] as string[],
  selected: [] as string[],
  custom: ''
})

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const isEdit = computed(() => !!currentItem.value)

const isValid = computed(() => {
  return form.value.name && form.value.category
})

// Initialize form from props
watch(
  () => props.modelValue,
  (newVal) => {
    if (newVal) {
      currentItem.value = props.item
      resetGenerator()
    }
    if (newVal && props.item) {
      form.value = {
        name: props.item.name,
        category: props.item.category || 0,
        base_unit: props.item.base_unit,
        attributes: props.item.attributes,
        is_variant_parent: props.item.is_variant_parent,
        is_standard_item: props.item.is_standard_item,
        size: props.item.size,
        identifier1: props.item.identifier1,
        identifier2: props.item.identifier2
      }
    } else if (newVal) {
      form.value = {
        name: '',
        category: 0,
        base_unit: 'Stück',
        attributes: null,
        is_variant_parent: false,
        is_standard_item: false,
        size: '',
        identifier1: '',
        identifier2: ''
      }
    }
    // Reset variant form
    variantForm.value = { attributes: {}, sku: '' }
    newAttributeKey.value = ''
  },
  { immediate: true }
)

const generatorCandidates = computed(() => generator.value.candidates)

const existingValues = computed(() => {
  const attribute = generator.value.attribute.trim()
  return new Set(
    (currentItem.value?.variants ?? [])
      .map((variant) => variant.variant_attributes?.[attribute])
      .filter((value): value is string => typeof value === 'string')
      .map((value) => value.trim().toLowerCase())
  )
})

const newGeneratorValues = computed(() =>
  generator.value.selected.filter((value) => !isExistingValue(value))
)

function isExistingValue(value: string): boolean {
  return existingValues.value.has(value.trim().toLowerCase())
}

function resetGenerator() {
  showGenerator.value = false
  generator.value = { presetKey: null, attribute: 'Größe', candidates: [], selected: [], custom: '' }
}

function toggleGenerator() {
  showGenerator.value = !showGenerator.value
}

function applyPreset() {
  const preset = SIZE_PRESETS.find((p) => p.key === generator.value.presetKey)
  generator.value.candidates = preset ? [...preset.values] : []
  selectAllCandidates()
}

function selectAllCandidates() {
  generator.value.selected = generator.value.candidates.filter((value) => !isExistingValue(value))
}

function toggleCandidate(value: string) {
  const selected = generator.value.selected
  generator.value.selected = selected.includes(value)
    ? selected.filter((v) => v !== value)
    : [...selected, value]
}

function addCustomValues() {
  const known = new Set(generator.value.candidates.map((v) => v.toLowerCase()))
  for (const value of parseSizeValues(generator.value.custom)) {
    if (!known.has(value.toLowerCase())) {
      generator.value.candidates.push(value)
      known.add(value.toLowerCase())
    }
    if (!generator.value.selected.includes(value) && !isExistingValue(value)) {
      generator.value.selected.push(value)
    }
  }
  generator.value.custom = ''
}

async function refreshItem() {
  if (currentItem.value) {
    currentItem.value = await inventoryStore.fetchItem(currentItem.value.id)
  }
}

async function generateVariants() {
  if (!currentItem.value) return
  const values = newGeneratorValues.value
  if (!values.length) return

  variantLoading.value = true
  try {
    const result = await inventoryStore.bulkCreateVariants({
      parent_item: currentItem.value.id,
      attribute: generator.value.attribute.trim(),
      values
    })
    await refreshItem()
    resetGenerator()
    toast.add({
      severity: 'success',
      summary: 'Erfolg',
      detail: result.skipped.length
        ? `${result.created.length} Varianten angelegt, ${result.skipped.length} bereits vorhanden`
        : `${result.created.length} Varianten angelegt`,
      life: 3000
    })
  } catch (err: unknown) {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: getApiErrorMessage(err, 'Varianten konnten nicht angelegt werden'),
      life: 5000
    })
  } finally {
    variantLoading.value = false
  }
}

function formatVariantAttributes(attrs: Record<string, string>): string {
  return Object.entries(attrs)
    .map(([k, v]) => `${k}: ${v}`)
    .join(', ')
}

function addAttribute() {
  if (newAttributeKey.value && newAttributeValue.value) {
    variantForm.value.attributes[newAttributeKey.value] = newAttributeValue.value
    newAttributeKey.value = ''
    newAttributeValue.value = ''
  }
}

function removeAttribute(key: string) {
  delete variantForm.value.attributes[key]
}

function openVariantDialog(variant: ItemVariant | null) {
  editingVariant.value = variant
  if (variant) {
    variantForm.value = {
      attributes: { ...variant.variant_attributes },
      sku: variant.sku || ''
    }
  } else {
    variantForm.value = { attributes: {}, sku: '' }
  }
  newAttributeKey.value = ''
  newAttributeValue.value = ''
  showVariantDialog.value = true
}

function confirmDeleteVariant(variant: ItemVariant) {
  confirm.require({
    group: 'variant',
    message: `Möchten Sie diese Variante wirklich löschen? (${formatVariantAttributes(variant.variant_attributes)})`,
    header: 'Variante löschen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Ja, löschen',
    rejectLabel: 'Abbrechen',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        await inventoryStore.deleteVariant(variant.id)
        await refreshItem()
        toast.add({
          severity: 'success',
          summary: 'Erfolg',
          detail: 'Variante wurde gelöscht',
          life: 3000
        })
      } catch (err: unknown) {
        const errorMessage = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Ein Fehler ist aufgetreten'
        toast.add({
          severity: 'error',
          summary: 'Fehler',
          detail: errorMessage,
          life: 5000
        })
      }
    }
  })
}

function closeDialog() {
  visible.value = false
}

async function submit() {
  if (!isValid.value) return

  loading.value = true
  try {
    let result: Item

    if (isEdit.value && currentItem.value) {
      result = await inventoryStore.updateItem(currentItem.value.id, form.value)
      toast.add({
        severity: 'success',
        summary: 'Erfolg',
        detail: 'Artikel wurde aktualisiert',
        life: 3000
      })
    } else {
      result = await inventoryStore.createItem(form.value as ItemCreate)
      if (result.is_variant_parent) {
        // Stay open so variants can be added right away.
        currentItem.value = result
        showGenerator.value = true
        toast.add({
          severity: 'success',
          summary: 'Artikel erstellt',
          detail: 'Jetzt Varianten anlegen oder Größen generieren',
          life: 4000
        })
        return
      }
      toast.add({
        severity: 'success',
        summary: 'Erfolg',
        detail: 'Artikel wurde erstellt',
        life: 3000
      })
    }

    emit('success', result)
    closeDialog()
  } catch (err: unknown) {
    const errorMessage = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Ein Fehler ist aufgetreten'
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: errorMessage,
      life: 5000
    })
  } finally {
    loading.value = false
  }
}

async function saveVariant() {
  if (!currentItem.value || Object.keys(variantForm.value.attributes).length === 0) return

  variantLoading.value = true
  try {
    if (editingVariant.value) {
      // Update existing variant
      await inventoryStore.updateVariant(editingVariant.value.id, {
        variant_attributes: variantForm.value.attributes,
        sku: variantForm.value.sku
      })
      toast.add({
        severity: 'success',
        summary: 'Erfolg',
        detail: 'Variante wurde aktualisiert',
        life: 3000
      })
    } else {
      // Create new variant
      await inventoryStore.createVariant({
        parent_item: currentItem.value.id,
        variant_attributes: variantForm.value.attributes,
        sku: variantForm.value.sku
      })
      toast.add({
        severity: 'success',
        summary: 'Erfolg',
        detail: 'Variante wurde hinzugefügt',
        life: 3000
      })
    }

    await refreshItem()

    showVariantDialog.value = false
    variantForm.value = { attributes: {}, sku: '' }
    editingVariant.value = null
  } catch (err: unknown) {
    const errorMessage = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Ein Fehler ist aufgetreten'
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: errorMessage,
      life: 5000
    })
  } finally {
    variantLoading.value = false
  }
}
</script>

<style scoped>
.item-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field label {
  font-weight: 600;
  font-size: 0.875rem;
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.variants-section {
  margin-top: 1rem;
}

.variants-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.variants-header h4 {
  margin: 0;
}

.variants-header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  justify-content: flex-end;
}

.generator {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem;
  margin-bottom: 1rem;
  border: 1px solid var(--p-content-border-color, var(--surface-border));
  border-radius: var(--border-radius);
}

.generator-values-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.size-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
}

.size-chip {
  min-width: 3rem;
  padding: 0.375rem 0.625rem;
  border: 1px solid var(--p-content-border-color, var(--surface-border));
  border-radius: 999px;
  background: transparent;
  color: inherit;
  font: inherit;
  font-size: 0.875rem;
  cursor: pointer;
}

.size-chip.selected {
  background: var(--p-primary-color);
  border-color: var(--p-primary-color);
  color: var(--p-primary-contrast-color);
}

.size-chip.existing {
  opacity: 0.5;
  cursor: not-allowed;
  text-decoration: line-through;
}

.size-chip:focus-visible {
  outline: 2px solid var(--p-primary-color);
  outline-offset: 2px;
}

.generator-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
}

@media (max-width: 600px) {
  .field-row {
    grid-template-columns: 1fr;
  }
}

.variants-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.variant-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem;
  background: var(--surface-ground);
  border-radius: var(--border-radius);
  gap: 1rem;
}

.variant-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
  min-width: 0;
}

.variant-name {
  font-weight: 500;
}

.variant-sku {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.variant-actions {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  flex-shrink: 0;
}

.empty-variants {
  text-align: center;
  padding: 1rem;
  color: var(--text-color-secondary);
}

.variant-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.attributes-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.attribute-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.attribute-row > :deep(.p-inputtext) {
  flex: 1;
}

.add-attribute-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  padding-top: 0.5rem;
  border-top: 1px solid var(--surface-border);
}

.add-attribute-row > :deep(.p-inputtext) {
  flex: 1;
}

.w-full {
  width: 100%;
}

.flex {
  display: flex;
}

.align-items-center {
  align-items: center;
}

.gap-2 {
  gap: 0.5rem;
}
</style>
