<template>
  <div class="lending-workbench">
    <div class="workbench-grid">
      <!-- Left: Ausgabe-Formular -->
      <Card class="form-card">
        <template #title>
          <div class="card-title">
            <i class="pi pi-user"></i>
            Ausleihe &amp; Ersteinkleidung
          </div>
        </template>
        <template #content>
          <div class="field">
            <label>Modus</label>
            <SelectButton
              v-model="mode"
              :options="modeOptions"
              option-label="label"
              option-value="value"
              class="mode-select"
            />
          </div>

          <div class="field">
            <label>An wen wird ausgegeben? *</label>
            <Select
              v-model="selectedMember"
              :options="memberOptions"
              option-label="label"
              option-value="value"
              placeholder="Mitglied auswählen..."
              filter
              filter-placeholder="Name suchen..."
              class="w-full"
            >
              <template #option="{ option }">
                <div class="member-option">
                  <i class="pi pi-user"></i>
                  <span>{{ option.label }}</span>
                </div>
              </template>
            </Select>
          </div>

          <Message v-if="mode === 'outfitting' && standardItems.length === 0" severity="warn" :closable="false">
            Es sind noch keine Standardartikel markiert. Artikel können in der Artikelverwaltung als
            Standardartikel gekennzeichnet werden.
          </Message>

          <div class="field">
            <div class="field-heading">
              <label>Artikel *</label>

            </div>

            <div v-for="(line, index) in lines" :key="line.id" class="loan-line">
              <Select
                v-model="line.itemId"
                :options="itemOptions"
                option-label="label"
                option-value="value"
                placeholder="Artikel auswählen..."
                filter
                class="item-select"
                @change="resetLine(line)"
              />
              <Select
                v-if="line.itemId && getItem(line.itemId)?.is_variant_parent"
                v-model="line.variantId"
                :options="getVariantOptions(line.itemId)"
                option-label="label"
                option-value="value"
                placeholder="Größe/Variante"
                class="variant-select"
                @change="line.sourceId = null"
              />
              <Select
                v-if="getSourceOptions(line).length > 1"
                v-model="line.sourceId"
                :options="getSourceOptions(line)"
                option-label="label"
                option-value="value"
                placeholder="Lagerort wählen"
                class="variant-select"
              />
              <InputNumber v-model="line.quantity" :min="1" show-buttons class="quantity-input" />
              <Tag
                v-if="getAvailable(line) >= line.quantity"
                :value="`${getAvailable(line)} verfügbar`"
                severity="success"
              />
              <Tag v-else :value="`${getAvailable(line)} verfügbar · ${line.quantity - getAvailable(line)} werden bestellt`" severity="warn" />
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

            <div class="field-footer">
              <Button label="Artikel hinzufügen" icon="pi pi-plus" text size="small" @click="addLine" />
            </div>
          </div>

          <div class="field">
            <label>Notiz (optional)</label>
            <InputText v-model="note" placeholder="z.B. Veranstaltung, Grund..." class="w-full" />
          </div>

          <Message v-if="validationMessage" severity="warn" :closable="false">
            {{ validationMessage }}
          </Message>

          <Message v-else-if="orderPreview.itemCount > 0" severity="warn" :closable="false">
            {{ orderPreview.itemCount }} Artikel ({{ orderPreview.totalQuantity }} Stück) sind nicht ausreichend
            vorrätig und werden bei der Ausgabe automatisch für das Mitglied bestellt.
          </Message>
          <Message v-else-if="selectedMember && lines.some((line) => line.itemId)" severity="success" :closable="false">
            Alle Artikel sind vorrätig und werden sofort ausgegeben.
          </Message>

          <div class="form-actions">
            <Button label="Zurücksetzen" severity="secondary" text :disabled="loading" @click="resetForm" />
            <Button
              label="Artikel ausgeben"
              icon="pi pi-check"
              :loading="loading"
              :disabled="!canSubmit"
              @click="submit"
            />
          </div>

          <div v-if="lastResult" class="result-panel">
            <Message severity="success" :closable="false">
              {{ lastResult.transactions.length }} Artikel sofort ausgegeben.
              <span v-if="lastResult.order"> {{ lastResult.missing_count }} Artikel wurden bestellt (Bestellung #{{ lastResult.order.id }}).</span>
            </Message>
          </div>
        </template>
      </Card>

      <!-- Right: Bestandsübersicht -->
      <div class="stock-column">
        <Card class="stock-card">
          <template #title>
            <div class="card-title">
              <i class="pi pi-box"></i>
              Bestandsübersicht
            </div>
          </template>
          <template #content>
            <div class="stock-filters">
              <IconField>
                <InputIcon class="pi pi-search" />
                <InputText v-model="stockSearch" placeholder="Artikel/Variante suchen..." />
              </IconField>
            </div>
            <DataTable
              :value="stockRows"
              :rows="10"
              :paginator="stockRows.length > 10"
              paginator-template="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink"
              striped-rows
              size="small"
              class="stock-table"
            >
              <Column field="display_name" header="Artikel">
                <template #body="{ data }">
                  {{ data.display_name }}
                </template>
              </Column>
              <Column field="location_name" header="Lagerort" style="width: 160px" />
              <Column field="quantity" header="Bestand" style="width: 100px; text-align: center">
                <template #body="{ data }">
                  <StockBadge :quantity="data.quantity" />
                </template>
              </Column>
              <template #empty>
                <div class="empty-table">
                  <i class="pi pi-inbox"></i>
                  <p>Keine Bestände gefunden</p>
                </div>
              </template>
            </DataTable>
          </template>
        </Card>

        <Card class="stock-card out-of-stock-card">
          <template #title>
            <div class="card-title">
              <i class="pi pi-exclamation-triangle"></i>
              Nicht vorrätig
            </div>
          </template>
          <template #content>
            <DataTable
              :value="outOfStockRows"
              :rows="10"
              :paginator="outOfStockRows.length > 10"
              paginator-template="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink"
              striped-rows
              size="small"
              class="stock-table"
            >
              <Column field="label" header="Artikel" />
              <Column header="" style="width: 60px">
                <template #body="{ data }">
                  <Button
                    icon="pi pi-plus"
                    size="small"
                    text
                    rounded
                    aria-label="Zur Ausgabe hinzufügen"
                    v-tooltip.top="'Zur Ausgabe hinzufügen'"
                    @click="addOutOfStockLine(data)"
                  />
                </template>
              </Column>
              <template #empty>
                <div class="empty-table">
                  <i class="pi pi-check-circle"></i>
                  <p>Alle Artikel sind vorrätig</p>
                </div>
              </template>
            </DataTable>
          </template>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import Card from 'primevue/card'
import SelectButton from 'primevue/selectbutton'
import Select from 'primevue/select'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import { useToast } from 'primevue/usetoast'
import { useInventoryStore } from '@/stores/inventory'
import { useMembersStore } from '@/stores/members'
import StockBadge from '../atoms/StockBadge.vue'
import type { BatchLoanResponse } from '@/types/inventory'

const inventoryStore = useInventoryStore()
const membersStore = useMembersStore()
const toast = useToast()

const loading = ref(false)
const mode = ref<'manual' | 'outfitting'>('manual')
const selectedMember = ref<number | null>(null)
const note = ref('')
const stockSearch = ref('')
const lastResult = ref<BatchLoanResponse | null>(null)

const modeOptions = [
  { label: 'Manuell', value: 'manual' },
  { label: 'Ersteinkleidung', value: 'outfitting' }
]

interface LoanLine {
  id: number
  itemId: number | null
  variantId: number | null
  quantity: number
  sourceId: number | null
}

let nextLineId = 1
function createLine(itemId: number | null = null): LoanLine {
  return { id: nextLineId++, itemId, variantId: null, quantity: 1, sourceId: null }
}

const lines = ref<LoanLine[]>([createLine()])

const memberOptions = computed(() =>
  membersStore.members.map((member) => ({ value: member.id, label: member.full_name }))
)

const itemOptions = computed(() =>
  inventoryStore.items.map((item) => ({
    value: item.id,
    label: item.name,
    category: item.category_name || undefined
  }))
)

const standardItems = computed(() => inventoryStore.items.filter((item) => item.is_standard_item))

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
  line.sourceId = null
  line.quantity = 1
}

function getSourceOptions(line: LoanLine) {
  if (!line.itemId || (getItem(line.itemId)?.is_variant_parent && !line.variantId)) return []
  return inventoryStore.stocks
    .filter((stock) => (line.variantId ? stock.item_variant === line.variantId : stock.item === line.itemId) && stock.quantity > 0)
    .filter((stock) => {
      const location = inventoryStore.locations.find((entry) => entry.id === stock.location)
      return location && !location.is_member
    })
    .map((stock) => ({ value: stock.location, label: `${stock.location_name} (${stock.quantity})` }))
}

function addLine() {
  lines.value.push(createLine())
}

function removeLine(index: number) {
  if (lines.value.length > 1) lines.value.splice(index, 1)
}

function getAvailableStock(type: 'item' | 'variant', id: number): number {
  return inventoryStore.stocks
    .filter((stock) => {
      const isCorrectItem = type === 'variant' ? stock.item_variant === id : stock.item === id
      if (!isCorrectItem) return false
      const location = inventoryStore.locations.find((l) => l.id === stock.location)
      return location && !location.is_member && stock.quantity > 0
    })
    .reduce((sum, stock) => sum + stock.quantity, 0)
}

function getAvailable(line: LoanLine) {
  if (!line.itemId) return 0
  if (line.sourceId) {
    const stock = inventoryStore.stocks.find((entry) => entry.location === line.sourceId &&
      (line.variantId ? entry.item_variant === line.variantId : entry.item === line.itemId))
    return stock?.quantity || 0
  }
  return line.variantId ? getAvailableStock('variant', line.variantId) : getAvailableStock('item', line.itemId)
}

function populateStandardItems() {
  lines.value = standardItems.value.length > 0 ? standardItems.value.map((item) => createLine(item.id)) : [createLine()]
}

watch(mode, (newMode) => {
  if (newMode === 'outfitting') {
    populateStandardItems()
  } else {
    lines.value = [createLine()]
  }
  lastResult.value = null
})

watch(selectedMember, () => {
  if (mode.value === 'outfitting') {
    populateStandardItems()
  }
  lastResult.value = null
})

const canSubmit = computed(() => {
  if (!selectedMember.value || lines.value.length === 0) return false
  const identities = lines.value.map((line) => `${line.variantId ? 'variant' : 'item'}:${line.variantId || line.itemId}`)
  if (new Set(identities).size !== identities.length) return false
  return lines.value.every((line) => {
    const item = getItem(line.itemId)
    return line.itemId && (!item?.is_variant_parent || line.variantId) && line.quantity > 0 &&
      (getSourceOptions(line).length <= 1 || line.sourceId !== null)
  })
})

const validationMessage = computed(() => {
  if (lines.value.some((line) => getSourceOptions(line).length > 1 && line.sourceId === null)) {
    return 'Bitte für Artikel mit Bestand an mehreren Lagerorten einen Quellort wählen.'
  }
  const identities = lines.value.map((line) => `${line.variantId ? 'variant' : 'item'}:${line.variantId || line.itemId}`)
  if (new Set(identities).size !== identities.length) return 'Ein Artikel darf nur einmal hinzugefügt werden.'
  if (lines.value.some((line) => line.itemId && getItem(line.itemId)?.is_variant_parent && !line.variantId)) {
    return 'Bitte für jeden Variantenartikel eine Größe auswählen.'
  }
  return null
})

const stockRows = computed(() => {
  const search = stockSearch.value.trim().toLowerCase()
  return inventoryStore.stocks
    .filter((stock) => {
      const location = inventoryStore.locations.find((l) => l.id === stock.location)
      if (location?.is_member) return false
      if (stock.quantity === 0) return false
      if (!search) return true
      return (stock.display_name || '').toLowerCase().includes(search)
    })
    .sort((a, b) => (a.display_name || '').localeCompare(b.display_name || ''))
})

interface OutOfStockRow {
  key: string
  label: string
  itemId: number
  variantId: number | null
}

const outOfStockRows = computed<OutOfStockRow[]>(() => {
  const search = stockSearch.value.trim().toLowerCase()
  const rows: OutOfStockRow[] = []

  inventoryStore.items.forEach((item) => {
    if (item.is_variant_parent) {
      ;(item.variants || []).forEach((variant) => {
        if (getAvailableStock('variant', variant.id) > 0) return
        const sizeLabel = Object.values(variant.variant_attributes || {}).join(' / ') || variant.sku
        const label = `${item.name} (${sizeLabel})`
        if (search && !label.toLowerCase().includes(search)) return
        rows.push({ key: `variant:${variant.id}`, label, itemId: item.id, variantId: variant.id })
      })
    } else {
      if (getAvailableStock('item', item.id) > 0) return
      if (search && !item.name.toLowerCase().includes(search)) return
      rows.push({ key: `item:${item.id}`, label: item.name, itemId: item.id, variantId: null })
    }
  })

  return rows.sort((a, b) => a.label.localeCompare(b.label))
})

function addOutOfStockLine(row: OutOfStockRow) {
  const existingLine = lines.value.find((line) =>
    row.variantId ? line.variantId === row.variantId : line.itemId === row.itemId && !line.variantId
  )
  if (existingLine) {
    existingLine.quantity += 1
    return
  }

  const emptyLineIndex = lines.value.findIndex((line) => !line.itemId)
  const newLine = createLine(row.itemId)
  newLine.variantId = row.variantId
  if (emptyLineIndex >= 0) {
    lines.value.splice(emptyLineIndex, 1, newLine)
  } else {
    lines.value.push(newLine)
  }
}

function resetForm() {
  mode.value = 'manual'
  selectedMember.value = null
  lines.value = [createLine()]
  note.value = ''
  lastResult.value = null
}

const orderPreview = computed(() => {
  const shortfallLines = lines.value.filter((line) => line.itemId && getAvailable(line) < line.quantity)
  return {
    itemCount: shortfallLines.length,
    totalQuantity: shortfallLines.reduce((sum, line) => sum + (line.quantity - getAvailable(line)), 0)
  }
})

async function submit() {
  if (!canSubmit.value || !selectedMember.value) return

  const orderMissing = orderPreview.value.itemCount > 0

  loading.value = true
  try {
    const result = await inventoryStore.batchLoan({
      member: selectedMember.value,
      items: lines.value.map((line) => ({
        item: line.variantId ? null : line.itemId,
        item_variant: line.variantId,
        quantity: line.quantity,
        source: line.sourceId || getSourceOptions(line)[0]?.value || undefined
      })),
      note: note.value,
      order_missing: orderMissing
    })

    lastResult.value = result

    toast.add({
      severity: 'success',
      summary: 'Ausgabe abgeschlossen',
      detail: result.missing_count > 0
        ? `${result.transactions.length} Artikel ausgegeben und ${result.missing_count} Artikel bestellt.`
        : `${result.transactions.length} Artikel wurden erfolgreich ausgegeben.`,
      life: 4000
    })

    const currentMember = selectedMember.value
    const currentMode = mode.value
    note.value = ''
    if (currentMode === 'outfitting') {
      lines.value = [createLine()]
      selectedMember.value = null
      mode.value = 'manual'
    } else {
      lines.value = [createLine()]
      selectedMember.value = currentMember
    }
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Ausgabe fehlgeschlagen. Bitte versuchen Sie es erneut.',
      life: 5000
    })
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.lending-workbench {
  display: flex;
  flex-direction: column;
}

.workbench-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
  gap: 1.5rem;
  align-items: start;
}

.stock-column {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

@media (max-width: 960px) {
  .workbench-grid {
    grid-template-columns: 1fr;
  }
}

.card-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1.25rem;
}

.field label {
  font-weight: 600;
  color: var(--text-color);
}

.mode-select {
  align-self: flex-start;
}

.field-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.field-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 0.5rem;
}

.member-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.loan-line {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
  flex-wrap: nowrap;
}

.item-select {
  flex: 2;
  min-width: 200px;
}

.variant-select {
  flex: 1;
  min-width: 140px;
}
.quantity-input {

}
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1rem;
}

.result-panel {
  margin-top: 1rem;
}

.stock-filters {
  margin-bottom: 0.75rem;
}

.stock-table {
  font-size: 0.9rem;
}

.empty-table {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1.5rem;
  color: var(--text-color-secondary);
}
</style>
