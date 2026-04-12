<template>
  <Dialog
    v-model:visible="visible"
    header="Artikel ausleihen"
    :style="{ width: '550px' }"
    modal
    :closable="!loading"
  >
    <div class="quick-loan-form">
      <!-- Step 1: Select Member -->
      <div class="field">
        <label>An wen wird ausgeliehen? *</label>
        <Dropdown
          v-model="selectedMember"
          :options="memberOptions"
          option-label="label"
          option-value="value"
          placeholder="Mitglied auswählen..."
          filter
          filter-placeholder="Name suchen..."
          class="w-full"
          :disabled="!!preselectedMember"
        >
          <template #option="{ option }">
            <div class="member-option">
              <i class="pi pi-user"></i>
              <span>{{ option.label }}</span>
            </div>
          </template>
        </Dropdown>
      </div>

      <!-- Step 2: Select Main Article -->
      <div class="field">
        <label>Welcher Artikel? *</label>
        <Dropdown
          v-model="selectedItem"
          :options="itemOptions"
          option-label="label"
          option-value="value"
          placeholder="Artikel auswählen..."
          filter
          filter-placeholder="Artikel suchen..."
          class="w-full"
        >
          <template #option="{ option }">
            <div class="article-option">
              <div class="article-info">
                <span class="article-name">{{ option.label }}</span>
                <Tag v-if="option.category" :value="option.category" severity="secondary" size="small" />
              </div>
              <div class="article-stock-info">
                <Tag
                  v-if="option.hasVariants"
                  value="Größen wählbar"
                  severity="info"
                  size="small"
                />
                <Tag
                  v-else
                  :value="`${option.available} verfügbar`"
                  :severity="option.available > 0 ? 'success' : 'danger'"
                  size="small"
                />
              </div>
            </div>
          </template>
          <template #value="{ value }">
            <span v-if="value">{{ getItemLabel(value) }}</span>
            <span v-else class="placeholder">Artikel auswählen...</span>
          </template>
        </Dropdown>
      </div>

      <!-- Step 2b: Select Size/Variant (if applicable) -->
      <div v-if="selectedItemHasVariants" class="field">
        <label>Welche Größe/Variante? *</label>
        <div class="variant-grid">
          <div
            v-for="variant in variantOptions"
            :key="variant.value"
            class="variant-card"
            :class="{
              selected: selectedVariant === variant.value,
              disabled: variant.available === 0
            }"
            @click="variant.available > 0 && (selectedVariant = variant.value)"
          >
            <div class="variant-size">{{ variant.sizeLabel }}</div>
            <div class="variant-availability">
              <Tag
                :value="`${variant.available} verfügbar`"
                :severity="variant.available > 0 ? 'success' : 'danger'"
                size="small"
              />
            </div>
            <div v-if="variant.bestSourceName" class="variant-source">
              {{ variant.bestSourceName }}
            </div>
          </div>
        </div>
      </div>

      <!-- Step 3: Quantity -->
      <div class="field">
        <label>Menge *</label>
        <div class="quantity-row">
          <InputNumber
            v-model="quantity"
            :min="1"
            :max="maxQuantity"
            show-buttons
            button-layout="horizontal"
            :input-style="{ width: '60px', textAlign: 'center' }"
          />
          <span class="available-text">
            von {{ maxQuantity }} verfügbar
            <span v-if="bestSourceName" class="source-hint">(aus {{ bestSourceName }})</span>
          </span>
        </div>
      </div>

      <!-- Optional Note -->
      <div class="field">
        <label>Notiz (optional)</label>
        <InputText v-model="note" placeholder="z.B. Veranstaltung, Grund..." class="w-full" />
      </div>

      <!-- Validation Message -->
      <Message v-if="validationMessage" severity="warn" :closable="false">
        {{ validationMessage }}
      </Message>
    </div>

    <template #footer>
      <Button label="Abbrechen" severity="secondary" text @click="closeDialog" :disabled="loading" />
      <Button
        label="Ausleihen"
        icon="pi pi-check"
        :loading="loading"
        @click="submit"
        :disabled="!isValid"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import Dialog from 'primevue/dialog'
import Dropdown from 'primevue/dropdown'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import { useInventoryStore } from '@/stores/inventory'
import { useToast } from 'primevue/usetoast'

interface Props {
  modelValue: boolean
  preselectedMember?: number
  preselectedItem?: number // Item ID (not "item:123" format)
}

const props = withDefaults(defineProps<Props>(), {
  preselectedMember: undefined,
  preselectedItem: undefined
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  success: []
}>()

const inventoryStore = useInventoryStore()
const toast = useToast()

const loading = ref(false)
const selectedMember = ref<number | null>(props.preselectedMember || null)
const selectedItem = ref<number | null>(props.preselectedItem || null)
const selectedVariant = ref<number | null>(null)
const quantity = ref(1)
const note = ref('')

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

// Member options from member locations
const memberOptions = computed(() => {
  return inventoryStore.memberLocations.map((l) => ({
    value: l.id,
    label: l.name,
    member_id: l.member
  }))
})

// Main article options (items only, not variants)
const itemOptions = computed(() => {
  const options: {
    value: number
    label: string
    category?: string
    hasVariants: boolean
    available: number
  }[] = []

  inventoryStore.items.forEach((item) => {
    if (item.is_variant_parent && item.variants?.length) {
      // Item with variants - show total available across all variants
      const totalAvailable = item.variants.reduce((sum, v) => {
        const stockInfo = getAvailableStock('variant', v.id)
        return sum + stockInfo.quantity
      }, 0)
      options.push({
        value: item.id,
        label: item.name,
        category: item.category_name || undefined,
        hasVariants: true,
        available: totalAvailable
      })
    } else {
      // Regular item without variants
      const stockInfo = getAvailableStock('item', item.id)
      options.push({
        value: item.id,
        label: item.name,
        category: item.category_name || undefined,
        hasVariants: false,
        available: stockInfo.quantity
      })
    }
  })

  // Sort: available items first, then by name
  return options.sort((a, b) => {
    if (a.available > 0 && b.available === 0) return -1
    if (a.available === 0 && b.available > 0) return 1
    return a.label.localeCompare(b.label)
  })
})

// Check if selected item has variants
const selectedItemHasVariants = computed(() => {
  const itemOption = itemOptions.value.find((o) => o.value === selectedItem.value)
  return itemOption?.hasVariants || false
})

// Get selected item's full object
const selectedItemObject = computed(() => {
  if (!selectedItem.value) return null
  return inventoryStore.items.find((i) => i.id === selectedItem.value)
})

// Variant options for selected item
const variantOptions = computed(() => {
  if (!selectedItemObject.value?.is_variant_parent) return []

  return (selectedItemObject.value.variants || []).map((variant) => {
    const stockInfo = getAvailableStock('variant', variant.id)
    
    // Extract size label from variant attributes
    const attrs = variant.variant_attributes || {}
    const sizeLabel = attrs.größe || attrs.groesse || attrs.size || 
                     attrs.Größe || attrs.Groesse || attrs.Size ||
                     Object.values(attrs).join(' / ') || 
                     `Variante ${variant.id}`

    return {
      value: variant.id,
      sizeLabel,
      available: stockInfo.quantity,
      bestSourceId: stockInfo.locationId,
      bestSourceName: stockInfo.locationName
    }
  }).sort((a, b) => {
    // Sort by size (try to parse as number first)
    const aNum = parseInt(a.sizeLabel)
    const bNum = parseInt(b.sizeLabel)
    if (!isNaN(aNum) && !isNaN(bNum)) return aNum - bNum
    return a.sizeLabel.localeCompare(b.sizeLabel)
  })
})

// Get available stock from storage locations (not member locations)
function getAvailableStock(type: string, id: number): {
  quantity: number
  locationId: number | null
  locationName: string | null
} {
  const relevantStocks = inventoryStore.stocks.filter((s) => {
    const isCorrectItem = type === 'variant' ? s.item_variant === id : s.item === id
    if (!isCorrectItem) return false

    const location = inventoryStore.locations.find((l) => l.id === s.location)
    return location && !location.is_member && s.quantity > 0
  })

  if (relevantStocks.length === 0) {
    return { quantity: 0, locationId: null, locationName: null }
  }

  // Sum all available and find best source
  const totalQuantity = relevantStocks.reduce((sum, s) => sum + s.quantity, 0)
  const bestStock = relevantStocks.reduce((best, current) =>
    current.quantity > best.quantity ? current : best
  )
  const bestLocation = inventoryStore.locations.find((l) => l.id === bestStock.location)

  return {
    quantity: totalQuantity,
    locationId: bestStock.location,
    locationName: bestLocation?.name || null
  }
}

// Selected stock info (either from variant or item)
const selectedStockInfo = computed(() => {
  if (selectedItemHasVariants.value) {
    if (!selectedVariant.value) return null
    return variantOptions.value.find((v) => v.value === selectedVariant.value)
  } else {
    if (!selectedItem.value) return null
    const stockInfo = getAvailableStock('item', selectedItem.value)
    return {
      available: stockInfo.quantity,
      bestSourceId: stockInfo.locationId,
      bestSourceName: stockInfo.locationName
    }
  }
})

const maxQuantity = computed(() => {
  return selectedStockInfo.value?.available || 0
})

const bestSourceName = computed(() => {
  return selectedStockInfo.value?.bestSourceName
})

const isValid = computed(() => {
  if (!selectedMember.value || !selectedItem.value) return false
  if (selectedItemHasVariants.value && !selectedVariant.value) return false
  return quantity.value > 0 && quantity.value <= maxQuantity.value
})

const validationMessage = computed(() => {
  if (selectedItem.value && !selectedItemHasVariants.value && maxQuantity.value === 0) {
    return 'Dieser Artikel ist nicht auf Lager.'
  }
  if (selectedVariant.value && maxQuantity.value === 0) {
    return 'Diese Größe ist nicht auf Lager.'
  }
  if (quantity.value > maxQuantity.value) {
    return `Nur ${maxQuantity.value} verfügbar.`
  }
  return null
})

function getItemLabel(value: number): string {
  const option = itemOptions.value.find((a) => a.value === value)
  return option?.label || String(value)
}

// Reset variant when item changes
watch(selectedItem, () => {
  selectedVariant.value = null
  quantity.value = 1
})

// Reset when dialog opens
watch(
  () => props.modelValue,
  (newVal) => {
    if (newVal) {
      selectedMember.value = props.preselectedMember || null
      selectedItem.value = props.preselectedItem || null
      selectedVariant.value = null
      quantity.value = 1
      note.value = ''
    }
  }
)

function closeDialog() {
  visible.value = false
}

async function submit() {
  if (!isValid.value || !selectedItem.value || !selectedMember.value) return

  loading.value = true
  try {
    // Determine if we're using a variant or item
    const useVariant = selectedItemHasVariants.value && selectedVariant.value
    const targetType = useVariant ? 'variant' : 'item'
    const targetId = useVariant ? selectedVariant.value! : selectedItem.value

    const stockInfo = getAvailableStock(targetType, targetId)
    const sourceId = stockInfo.locationId

    if (!sourceId) {
      throw new Error('Keine Quelle gefunden')
    }

    await inventoryStore.createTransaction({
      transaction_type: 'LOAN',
      item: useVariant ? null : selectedItem.value,
      item_variant: useVariant ? selectedVariant.value : null,
      source: sourceId,
      target: selectedMember.value,
      quantity: quantity.value,
      note: note.value
    })

    const itemLabel = getItemLabel(selectedItem.value)
    const variantLabel = useVariant 
      ? variantOptions.value.find((v) => v.value === selectedVariant.value)?.sizeLabel 
      : ''

    toast.add({
      severity: 'success',
      summary: 'Ausgeliehen',
      detail: `${quantity.value}x ${itemLabel}${variantLabel ? ` (${variantLabel})` : ''} erfolgreich ausgeliehen.`,
      life: 3000
    })

    emit('success')
    closeDialog()
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Ausleihe fehlgeschlagen. Bitte versuchen Sie es erneut.',
      life: 5000
    })
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.quick-loan-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field label {
  font-weight: 600;
  color: var(--text-color);
}

.member-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.article-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  gap: 1rem;
}

.article-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
  min-width: 0;
}

.article-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.article-stock-info {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

/* Variant Grid */
.variant-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 0.75rem;
}

.variant-card {
  border: 2px solid var(--surface-border);
  border-radius: 8px;
  padding: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
}

.variant-card:hover:not(.disabled) {
  border-color: var(--primary-color);
  background-color: var(--surface-hover);
}

.variant-card.selected{
  border: 1px solid var(--p-primary-400)
}

.variant-card.disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background-color: var(--surface-100);
}

.variant-size {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-color);
  margin-bottom: 0.5rem;
}

.variant-availability {
  margin-bottom: 0.25rem;
}

.variant-source {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.quantity-row {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.available-text {
  color: var(--text-color-secondary);
  font-size: 0.875rem;
}

.source-hint {
  font-style: italic;
}

.placeholder {
  color: var(--text-color-secondary);
}
</style>
