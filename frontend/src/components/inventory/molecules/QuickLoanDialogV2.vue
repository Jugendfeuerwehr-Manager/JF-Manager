<template>
  <Dialog
    v-model:visible="visible"
    header="Artikel ausleihen"
    :style="{ width: '550px' }"
    modal
    :closable="!loading"
  >
    <div class="quick-loan-form">
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

      <div class="field">
        <div class="field-heading">
          <label>Artikel *</label>
          <Button label="Artikel hinzufügen" icon="pi pi-plus" text size="small" @click="addLine" />
        </div>
        <div v-for="(line, index) in lines" :key="line.id" class="loan-line">
          <Dropdown
            v-model="line.itemId"
            :options="itemOptions"
            option-label="label"
            option-value="value"
            placeholder="Artikel auswählen..."
            filter
            class="item-select"
            @change="resetLine(line)"
          />
          <Dropdown
            v-if="line.itemId && getItem(line.itemId)?.is_variant_parent"
            v-model="line.variantId"
            :options="getVariantOptions(line.itemId)"
            option-label="label"
            option-value="value"
            placeholder="Größe/Variante"
            class="variant-select"
          />
          <InputNumber v-model="line.quantity" :min="1" :max="getAvailable(line)" show-buttons class="quantity-input" />
          <Tag :value="`${getAvailable(line)} verfügbar`" :severity="getAvailable(line) > 0 ? 'success' : 'danger'" />
          <Button
            icon="pi pi-trash"
            severity="danger"
            text
            rounded
            aria-label="Artikel entfernen"
            :disabled="lines.length === 1"
            @click="removeLine(index)"
          />
        </div>
      </div>

      <!-- Optional Note -->
      <div class="field">
        <label>Notiz (optional)</label>
        <InputText v-model="note" placeholder="z.B. Veranstaltung, Grund..." class="w-full" />
      </div>

      <Message v-if="validationMessage" severity="warn" :closable="false">
        {{ validationMessage }}
      </Message>
    </div>

    <template #footer>
      <Button label="Abbrechen" severity="secondary" text @click="closeDialog" :disabled="loading" />
      <Button
        label="Artikel ausgeben"
        icon="pi pi-check"
        :loading="loading"
        @click="submit"
        :disabled="!canSubmit"
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
import { useMembersStore } from '@/stores/members'
import { useToast } from 'primevue/usetoast'

interface Props {
  modelValue: boolean
  preselectedMember?: number
  preselectedItem?: number // Item ID (not "item:123" format)
  firstOutfitting?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  preselectedMember: undefined,
  preselectedItem: undefined,
  firstOutfitting: false
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  success: []
}>()

const inventoryStore = useInventoryStore()
const membersStore = useMembersStore()
const toast = useToast()

const loading = ref(false)
const selectedMember = ref<number | null>(props.preselectedMember || null)
const note = ref('')

interface LoanLine {
  id: number
  itemId: number | null
  variantId: number | null
  quantity: number
}

let nextLineId = 1
const lines = ref<LoanLine[]>([createLine(props.preselectedItem)])

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const memberOptions = computed(() => {
  return membersStore.members.map((member) => ({ value: member.id, label: member.full_name }))
})

const itemOptions = computed(() => {
  return inventoryStore.items.map((item) => ({
    value: item.id,
    label: item.name,
    category: item.category_name || undefined
  }))
})

function createLine(itemId: number | undefined = undefined): LoanLine {
  return { id: nextLineId++, itemId: itemId || null, variantId: null, quantity: 1 }
}

function getItem(itemId: number | null) {
  return itemId ? inventoryStore.items.find((item) => item.id === itemId) : undefined
}

function getVariantOptions(itemId: number) {
  return (getItem(itemId)?.variants || []).map((variant) => ({
    value: variant.id,
    label: Object.values(variant.variant_attributes || {}).join(' / ') || variant.sku
  }))
}

function resetLine(line: LoanLine) {
  line.variantId = null
  line.quantity = 1
}

function addLine() {
  lines.value.push(createLine())
}

function removeLine(index: number) {
  if (lines.value.length > 1) lines.value.splice(index, 1)
}

// Get available stock from storage locations (not member locations)
function getAvailableStock(type: 'item' | 'variant', id: number): number {
  const relevantStocks = inventoryStore.stocks.filter((s) => {
    const isCorrectItem = type === 'variant' ? s.item_variant === id : s.item === id
    if (!isCorrectItem) return false

    const location = inventoryStore.locations.find((l) => l.id === s.location)
    return location && !location.is_member && s.quantity > 0
  })
  return relevantStocks.reduce((sum, stock) => sum + stock.quantity, 0)
}

function getAvailable(line: LoanLine) {
  if (!line.itemId) return 0
  return line.variantId
    ? getAvailableStock('variant', line.variantId)
    : getAvailableStock('item', line.itemId)
}

const canSubmit = computed(() => {
  if (!selectedMember.value || lines.value.length === 0) return false
  const identities = lines.value.map((line) => `${line.variantId ? 'variant' : 'item'}:${line.variantId || line.itemId}`)
  if (new Set(identities).size !== identities.length) return false
  return lines.value.every((line) => {
    const item = getItem(line.itemId)
    return line.itemId && (!item?.is_variant_parent || line.variantId) && line.quantity > 0
  })
})

const validationMessage = computed(() => {
  const identities = lines.value.map((line) => `${line.variantId ? 'variant' : 'item'}:${line.variantId || line.itemId}`)
  if (new Set(identities).size !== identities.length) return 'Ein Artikel darf nur einmal hinzugefügt werden.'
  if (lines.value.some((line) => line.itemId && getAvailable(line) === 0)) return 'Mindestens ein Artikel ist nicht auf Lager.'
  if (lines.value.some((line) => line.itemId && line.quantity > getAvailable(line))) return 'Eine Menge ist größer als der verfügbare Bestand.'
  if (lines.value.some((line) => line.itemId && getItem(line.itemId)?.is_variant_parent && !line.variantId)) return 'Bitte für jeden Variantenartikel eine Größe auswählen.'
  return null
})

// Reset when dialog opens
watch(
  () => props.modelValue,
  async (newVal) => {
    if (newVal) {
      selectedMember.value = props.preselectedMember || null
      lines.value = props.firstOutfitting
        ? inventoryStore.items.filter((item) => item.is_standard_item).map((item) => createLine(item.id))
        : [createLine(props.preselectedItem)]
      note.value = ''
      if (membersStore.members.length === 0) await membersStore.fetchMembers({ limit: 1000 })
    }
  }
)

function closeDialog() {
  visible.value = false
}

async function submit() {
  if (!canSubmit.value || !selectedMember.value) return

  loading.value = true
  try {
    const hasMissingItems = lines.value.some((line) => getAvailable(line) < line.quantity)
    const orderMissing = hasMissingItems
      ? window.confirm('Einige Artikel sind nicht ausreichend vorhanden. Sollen diese bestellt werden?')
      : false

    if (hasMissingItems && !orderMissing) return

    const result = await inventoryStore.batchLoan({
      member: selectedMember.value,
      items: lines.value.map((line) => ({
        item: line.variantId ? null : line.itemId,
        item_variant: line.variantId,
        quantity: line.quantity
      })),
      note: note.value,
      order_missing: orderMissing
    })

    toast.add({
      severity: 'success',
      summary: 'Ausgabe abgeschlossen',
      detail: result.missing_count > 0
        ? `${result.transactions.length} Artikel ausgegeben und ${result.missing_count} Artikel bestellt.`
        : `${result.transactions.length} Artikel wurden erfolgreich ausgegeben.`,
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
