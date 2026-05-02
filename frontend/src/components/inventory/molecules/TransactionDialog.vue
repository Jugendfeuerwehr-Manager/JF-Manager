<template>
  <Dialog
    v-model:visible="visible"
    :header="dialogTitle"
    :style="{ width: '500px' }"
    modal
    :closable="!loading"
  >
    <div class="transaction-form">
      <!-- Transaction Type Selection -->
      <div class="field">
        <label for="transactionType">Transaktionstyp *</label>
        <Dropdown
          id="transactionType"
          v-model="form.transaction_type"
          :options="transactionTypeOptions"
          option-label="label"
          option-value="value"
          placeholder="Typ auswählen"
          class="w-full"
          :disabled="!!initialType"
        />
      </div>

      <!-- Item Selection (Step 1: Main Item) -->
      <div class="field">
        <label for="item">Artikel *</label>
        <Dropdown
          id="item"
          v-model="selectedMainItem"
          :options="mainItemOptions"
          option-label="label"
          option-value="value"
          placeholder="Artikel auswählen"
          filter
          class="w-full"
          :disabled="!!initialStock"
        >
          <template #option="{ option }">
            <div class="item-option">
              <div class="item-info">
                <span>{{ option.label }}</span>
                <Tag v-if="option.category" :value="option.category" severity="secondary" size="small" />
              </div>
              <div class="item-stock-info">
                <Tag
                  v-if="option.hasVariants"
                  value="Varianten wählbar"
                  severity="info"
                  size="small"
                />
                <Tag
                  v-else
                  :value="`${option.available} verf.`"
                  :severity="option.available > 0 ? 'success' : 'danger'"
                  size="small"
                />
              </div>
            </div>
          </template>
          <template #value="{ value }">
            <span v-if="value">{{ getMainItemLabel(value) }}</span>
            <span v-else class="placeholder">Artikel auswählen...</span>
          </template>
        </Dropdown>
      </div>

      <!-- Variant Selection (Step 2: if item has variants) -->
      <div v-if="selectedItemHasVariants" class="field">
        <label>Größe/Variante *</label>
        <div class="variant-grid">
          <div
            v-for="variant in variantOptionsForItem"
            :key="variant.value"
            class="variant-card"
            :class="{
              selected: selectedVariantId === variant.value
            }"
            @click="selectVariant(variant.value)"
          >
            <div class="variant-size">{{ variant.sizeLabel }}</div>
            <div class="variant-availability">
              <Tag
                :value="`${variant.available} verf.`"
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

      <!-- Source Location (for OUT, MOVE, LOAN, DISCARD) -->
      <div v-if="needsSource" class="field">
        <label for="source">Quelle *</label>
        <Dropdown
          id="source"
          v-model="form.source"
          :options="sourceOptions"
          option-label="label"
          option-value="value"
          placeholder="Quelle auswählen"
          filter
          class="w-full"
          :disabled="!!initialStock"
        >
          <template #option="{ option }">
            <div class="location-option">
              <i :class="option.is_member ? 'pi pi-user' : 'pi pi-box'"></i>
              <span>{{ option.label }}</span>
            </div>
          </template>
        </Dropdown>
      </div>

      <!-- Target Location (for IN, MOVE, LOAN, RETURN) -->
      <div v-if="needsTarget" class="field">
        <label for="target">Ziel *</label>
        <Dropdown
          id="target"
          v-model="form.target"
          :options="targetOptions"
          option-label="label"
          option-value="value"
          placeholder="Ziel auswählen"
          filter
          class="w-full"
        >
          <template #option="{ option }">
            <div class="location-option">
              <i :class="option.is_member ? 'pi pi-user' : 'pi pi-box'"></i>
              <span>{{ option.label }}</span>
            </div>
          </template>
        </Dropdown>
      </div>

      <!-- Quantity -->
      <div class="field">
        <label for="quantity">Menge *</label>
        <InputNumber
          id="quantity"
          v-model="form.quantity"
          :min="1"
          :max="maxQuantity"
          show-buttons
          class="w-full"
        />
        <small v-if="maxQuantity && maxQuantity < Infinity" class="text-muted">
          Verfügbar: {{ maxQuantity }}
        </small>
      </div>

      <!-- Discard Reason (only for DISCARD transactions) -->
      <div v-if="form.transaction_type === 'DISCARD'" class="field">
        <label for="discardReason">Aussortierungsgrund *</label>
        <Dropdown
          id="discardReason"
          v-model="form.discard_reason"
          :options="discardReasonOptions"
          option-label="label"
          option-value="value"
          placeholder="Grund auswählen"
          class="w-full"
        >
          <template #option="{ option }">
            <div class="flex align-items-center gap-2">
              <i :class="['pi', option.icon]"></i>
              <span>{{ option.label }}</span>
            </div>
          </template>
        </Dropdown>
      </div>

      <!-- Notes -->
      <div class="field">
        <label for="note">Notiz</label>
        <Textarea
          id="note"
          v-model="form.note"
          rows="2"
          class="w-full"
          placeholder="Optionale Notiz..."
        />
      </div>
    </div>

    <template #footer>
      <Button label="Abbrechen" severity="secondary" text @click="closeDialog" :disabled="loading" />
      <Button
        :label="submitLabel"
        :icon="submitIcon"
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
import Textarea from 'primevue/textarea'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { useInventoryStore } from '@/stores/inventory'
import { useToast } from 'primevue/usetoast'
import type { TransactionType, TransactionCreate, Stock } from '@/types/inventory'
import { TRANSACTION_TYPES, DISCARD_REASONS } from '@/types/inventory'

interface Props {
  modelValue: boolean
  initialType?: TransactionType
  initialStock?: Stock
}

const props = withDefaults(defineProps<Props>(), {
  initialType: undefined,
  initialStock: undefined
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  success: [transaction: unknown]
}>()

const inventoryStore = useInventoryStore()
const toast = useToast()

const loading = ref(false)
const form = ref<TransactionCreate>({
  transaction_type: props.initialType || 'IN',
  item: null,
  item_variant: null,
  source: null,
  target: null,
  quantity: 1,
  note: '',
  discard_reason: null
})

const discardReasonOptions = DISCARD_REASONS

// Two-step selection: main item, then variant (if applicable)
const selectedMainItem = ref<number | null>(null)
const selectedVariantId = ref<number | null>(null)

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const dialogTitle = computed(() => {
  const typeLabel = TRANSACTION_TYPES.find((t) => t.value === form.value.transaction_type)?.label || 'Transaktion'
  return `Neue ${typeLabel}`
})

const transactionTypeOptions = TRANSACTION_TYPES.map((t) => ({
  value: t.value,
  label: t.label
}))

// Main item options (parent items, not individual variants)
const mainItemOptions = computed(() => {
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
        const stockInfo = getAvailableStockForType('variant', v.id)
        return sum + stockInfo.quantity
      }, 0)
      options.push({
        value: item.id,
        label: `${item.name}${item.department === null ? ' [G]' : ''}`,
        category: item.category_name || undefined,
        hasVariants: true,
        available: totalAvailable
      })
    } else {
      // Regular item without variants
      const stockInfo = getAvailableStockForType('item', item.id)
      options.push({
        value: item.id,
        label: `${item.name}${item.department === null ? ' [G]' : ''}`,
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
  const itemOption = mainItemOptions.value.find((o) => o.value === selectedMainItem.value)
  return itemOption?.hasVariants || false
})

// Get selected item's full object
const selectedItemObject = computed(() => {
  if (!selectedMainItem.value) return null
  return inventoryStore.items.find((i) => i.id === selectedMainItem.value)
})

// Variant options for the selected item
const variantOptionsForItem = computed(() => {
  if (!selectedItemObject.value?.is_variant_parent) return []

  return (selectedItemObject.value.variants || []).map((variant) => {
    const stockInfo = getAvailableStockForType('variant', variant.id)
    
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

// Helper function to get label for selected main item
function getMainItemLabel(itemId: number): string {
  const item = mainItemOptions.value.find((o) => o.value === itemId)
  return item?.label || ''
}

// Helper to select a variant
function selectVariant(variantId: number) {
  selectedVariantId.value = variantId
}

// Get available stock based on transaction type
function getAvailableStockForType(type: string, id: number): {
  quantity: number
  locationId: number | null
  locationName: string | null
} {
  const transactionType = form.value.transaction_type
  // For RETURN, look in member locations
  // For other types needing source, look in storage locations
  const shouldLookInMemberLocations = transactionType === 'RETURN'

  const relevantStocks = inventoryStore.stocks.filter((s) => {
    const isCorrectItem = type === 'variant' ? s.item_variant === id : s.item === id
    if (!isCorrectItem) return false

    const location = inventoryStore.locations.find((l) => l.id === s.location)
    if (!location) return false

    const isCorrectLocationType = shouldLookInMemberLocations ? location.is_member : !location.is_member
    return isCorrectLocationType && s.quantity > 0
  })

  if (relevantStocks.length === 0) {
    return { quantity: 0, locationId: null, locationName: null }
  }

  // Sum total quantity and find best source
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

const sourceOptions = computed(() => {
  // For LOAN, source should be storage locations (not members)
  if (form.value.transaction_type === 'LOAN') {
    return inventoryStore.storageLocations.map((l) => ({
      value: l.id,
      label: `${l.full_path || l.name}${l.department === null ? ' [G]' : ''}`,
      is_member: false
    }))
  }
  // For RETURN, source should be member locations
  if (form.value.transaction_type === 'RETURN') {
    return inventoryStore.memberLocations.map((l) => ({
      value: l.id,
      label: `${l.full_path || l.name}${l.department === null ? ' [G]' : ''}`,
      is_member: true
    }))
  }
  return inventoryStore.locationOptions
})

const targetOptions = computed(() => {
  // For LOAN, target should be member locations
  if (form.value.transaction_type === 'LOAN') {
    return inventoryStore.memberLocations.map((l) => ({
      value: l.id,
      label: `${l.full_path || l.name}${l.department === null ? ' [G]' : ''}`,
      is_member: true
    }))
  }
  // For RETURN, target should be storage locations
  if (form.value.transaction_type === 'RETURN') {
    return inventoryStore.storageLocations.map((l) => ({
      value: l.id,
      label: `${l.full_path || l.name}${l.department === null ? ' [G]' : ''}`,
      is_member: false
    }))
  }
  return inventoryStore.locationOptions
})

const needsSource = computed(() => {
  return ['OUT', 'MOVE', 'LOAN', 'DISCARD'].includes(form.value.transaction_type)
})

const needsTarget = computed(() => {
  return ['IN', 'MOVE', 'LOAN', 'RETURN'].includes(form.value.transaction_type)
})

const maxQuantity = computed(() => {
  if (!needsSource.value || !form.value.source) {
    return Infinity
  }

  // Use variant if selected, otherwise main item
  if (selectedVariantId.value) {
    const stock = inventoryStore.stocks.find((s) => 
      s.item_variant === selectedVariantId.value && s.location === form.value.source
    )
    return stock?.quantity || 0
  } else if (selectedMainItem.value && !selectedItemHasVariants.value) {
    const stock = inventoryStore.stocks.find((s) => 
      s.item === selectedMainItem.value && s.location === form.value.source
    )
    return stock?.quantity || 0
  }

  return Infinity
})

const submitLabel = computed(() => {
  return TRANSACTION_TYPES.find((t) => t.value === form.value.transaction_type)?.label || 'Speichern'
})

const submitIcon = computed(() => {
  const type = TRANSACTION_TYPES.find((t) => t.value === form.value.transaction_type)
  return type ? `pi ${type.icon}` : 'pi pi-check'
})

const isValid = computed(() => {
  // Need either a regular item or a variant selected
  if (!selectedMainItem.value) return false
  if (selectedItemHasVariants.value && !selectedVariantId.value) return false
  
  if (!form.value.quantity || form.value.quantity < 1) return false
  if (needsSource.value && !form.value.source) return false
  if (needsTarget.value && !form.value.target) return false
  if (needsSource.value && form.value.quantity > maxQuantity.value) return false
  if (form.value.transaction_type === 'DISCARD' && !form.value.discard_reason) return false
  return true
})

// Initialize from props
watch(
  () => props.modelValue,
  (newVal) => {
    if (newVal) {
      // Reset form
      form.value = {
        transaction_type: props.initialType || 'IN',
        item: null,
        item_variant: null,
        source: props.initialStock?.location || null,
        target: null,
        quantity: 1,
        note: '',
        discard_reason: null
      }

      // Set initial item/variant selection
      if (props.initialStock) {
        if (props.initialStock.item_variant) {
          // Find parent item for this variant
          const variant = inventoryStore.items
            .flatMap(i => i.variants || [])
            .find(v => v.id === props.initialStock?.item_variant)
          if (variant) {
            selectedMainItem.value = variant.parent_item
            selectedVariantId.value = props.initialStock.item_variant
          }
        } else if (props.initialStock.item) {
          selectedMainItem.value = props.initialStock.item
          selectedVariantId.value = null
        }
      } else {
        selectedMainItem.value = null
        selectedVariantId.value = null
      }
    }
  },
  { immediate: true }
)

// When main item changes, reset variant and update form
watch(selectedMainItem, (itemId) => {
  // Reset variant selection when main item changes
  selectedVariantId.value = null
  
  if (!itemId) {
    form.value.item = null
    form.value.item_variant = null
    return
  }

  // If item has no variants, set it directly
  if (!selectedItemHasVariants.value) {
    form.value.item = itemId
    form.value.item_variant = null
    
    // Auto-select source
    if (needsSource.value && !props.initialStock) {
      autoSelectBestSource('item', itemId)
    }
  }
})

// When variant changes, update form and auto-select source
watch(selectedVariantId, (variantId) => {
  if (!variantId) {
    // If item doesn't have variants, keep item set
    if (!selectedItemHasVariants.value && selectedMainItem.value) {
      form.value.item = selectedMainItem.value
    } else {
      form.value.item = null
    }
    form.value.item_variant = null
    return
  }

  form.value.item = null
  form.value.item_variant = variantId
  
  // Auto-select source with most stock
  if (needsSource.value && !props.initialStock) {
    autoSelectBestSource('variant', variantId)
  }
})

// Auto-select the source location with the most stock of the selected item
function autoSelectBestSource(type: string, id: number) {
  const transactionType = form.value.transaction_type

  // For RETURN, look in member locations
  // For LOAN/OUT/MOVE/DISCARD, look in storage locations
  const shouldLookInMemberLocations = transactionType === 'RETURN'

  // Find all stock entries for this item in the appropriate location type
  const relevantStocks = inventoryStore.stocks.filter((s) => {
    const isCorrectItem = type === 'variant' ? s.item_variant === id : s.item === id
    if (!isCorrectItem) return false

    const location = inventoryStore.locations.find((l) => l.id === s.location)
    if (!location) return false

    // Check location type matches what we need
    const isCorrectLocationType = shouldLookInMemberLocations ? location.is_member : !location.is_member

    return isCorrectLocationType && s.quantity > 0
  })

  if (relevantStocks.length === 0) {
    form.value.source = null
    return
  }

  // Find the one with the most quantity
  const bestStock = relevantStocks.reduce((best, current) =>
    current.quantity > best.quantity ? current : best
  )

  form.value.source = bestStock.location
}

// Watch for transaction type changes and re-trigger auto-select
watch(
  () => form.value.transaction_type,
  () => {
    // Reset source/target and discard_reason when type changes (unless we have initialStock)
    form.value.discard_reason = null
    if (!props.initialStock) {
      form.value.source = null
      form.value.target = null

      // Re-trigger auto-select if we have an item or variant selected
      if (selectedVariantId.value && needsSource.value) {
        autoSelectBestSource('variant', selectedVariantId.value)
      } else if (selectedMainItem.value && !selectedItemHasVariants.value && needsSource.value) {
        autoSelectBestSource('item', selectedMainItem.value)
      }
    }
  }
)

function closeDialog() {
  visible.value = false
}

async function submit() {
  if (!isValid.value) return

  loading.value = true
  try {
    const data: TransactionCreate = {
      transaction_type: form.value.transaction_type,
      quantity: form.value.quantity,
      note: form.value.note || ''
    }

    if (form.value.item) data.item = form.value.item
    if (form.value.item_variant) data.item_variant = form.value.item_variant
    if (form.value.source) data.source = form.value.source
    if (form.value.target) data.target = form.value.target
    if (form.value.transaction_type === 'DISCARD' && form.value.discard_reason) {
      data.discard_reason = form.value.discard_reason
    }

    const result = await inventoryStore.createTransaction(data)

    toast.add({
      severity: 'success',
      summary: 'Erfolg',
      detail: `${submitLabel.value} wurde erfolgreich durchgeführt`,
      life: 3000
    })

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
</script>

<style scoped>
.transaction-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.variant-card.selected {
    border: 1px solid var(--p-primary-400, #007ad9);
    border-radius: .5rem;
    background: color-mix(in srgb, var(--p-primary-400) 15%, transparent);
    box-shadow: 0 0 0 1px var(--p-primary-400);
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

.item-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  gap: 0.5rem;
}

.item-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
  min-width: 0;
}

.item-stock-info {
  flex-shrink: 0;
}

.location-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.placeholder {
  color: var(--text-color-secondary);
}

/* Variant Grid */
.variant-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 0.5rem;
}

.variant-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.75rem 0.5rem;
  border: 2px solid var(--surface-border);
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: all 0.2s;
  background: var(--surface-card);
  text-align: center;
}

.variant-card:hover:not(.disabled) {
  border-color: var(--primary-color);
  background: var(--surface-hover);
}

.variant-card.selected {
  border-color: var(--primary-color);
  background: color-mix(in srgb, var(--primary-color) 15%, transparent);
  box-shadow: 0 0 0 1px var(--primary-color);
}

.variant-size {
  font-weight: 600;
  font-size: 1rem;
  margin-bottom: 0.25rem;
}

.variant-availability {
  margin-bottom: 0.25rem;
}

.variant-source {
  font-size: 0.7rem;
  color: var(--text-color-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}
.text-muted {
  color: var(--text-color-secondary);
}

.w-full {
  width: 100%;
}
</style>
