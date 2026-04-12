<template>
  <div class="transactions-history">
    <!-- Header -->
    <div class="section-header">
      <h3>
        <i class="pi pi-history"></i>
        Transaktions-Verlauf
      </h3>
      <Button label="Neue Transaktion" icon="pi pi-plus" @click="showTransactionDialog = true" />
    </div>

    <!-- Filters -->
    <Card class="filter-card">
      <template #content>
        <div class="filter-grid">
          <IconField>
            <InputIcon class="pi pi-search" />
            <InputText v-model="filters.search" placeholder="Suchen..." @input="onFilterChange" />
          </IconField>

          <Dropdown
            v-model="filters.type"
            :options="transactionTypeOptions"
            option-label="label"
            option-value="value"
            placeholder="Transaktionstyp"
            show-clear
            @change="onFilterChange"
          />

          <DatePicker
            v-model="filters.dateFrom"
            placeholder="Von Datum"
            date-format="dd.mm.yy"
            show-icon
            fluid
            updateModelType="date"
          />

          <DatePicker
            v-model="filters.dateTo"
            placeholder="Bis Datum"
            date-format="dd.mm.yy"
            show-icon
            fluid
            updateModelType="date"
          />
        </div>
      </template>
    </Card>

    <!-- Transactions Table -->
    <Card class="table-card">
      <template #content>
        <DataTable
          :value="filteredTransactions"
          :loading="inventoryStore.transactionsLoading"
          :paginator="true"
          :rows="20"
          :rows-per-page-options="[10, 20, 50]"
          paginator-template="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
          current-page-report-template="{first} bis {last} von {totalRecords}"
          striped-rows
          removable-sort
          sort-field="date"
          :sort-order="-1"
        >
          <Column field="date" header="Datum" sortable style="width: 150px">
            <template #body="{ data }">
              {{ formatDate(data.date) }}
            </template>
          </Column>

          <Column field="transaction_type" header="Typ" sortable style="width: 140px">
            <template #body="{ data }">
              <TransactionTypeBadge :type="data.transaction_type" />
            </template>
          </Column>

          <Column field="item_name" header="Artikel" sortable>
            <template #body="{ data }">
              <span class="item-name">{{ data.item_name }}</span>
            </template>
          </Column>

          <Column field="quantity" header="Menge" sortable style="width: 100px; text-align: center">
            <template #body="{ data }">
              <Badge :value="data.quantity" severity="secondary" />
            </template>
          </Column>

          <Column header="Von / Nach" style="width: 250px">
            <template #body="{ data }">
              <div class="location-flow">
                <span v-if="data.source_name" class="source">
                  <i class="pi pi-sign-out"></i>
                  {{ data.source_name }}
                </span>
                <i v-if="data.source_name && data.target_name" class="pi pi-arrow-right flow-arrow"></i>
                <span v-if="data.target_name" class="target">
                  <i class="pi pi-sign-in"></i>
                  {{ data.target_name }}
                </span>
              </div>
            </template>
          </Column>

          <Column field="user_username" header="Benutzer" sortable style="width: 130px">
            <template #body="{ data }">
              <span class="user-name">{{ data.user_username || '-' }}</span>
            </template>
          </Column>

          <Column field="note" header="Notiz" style="width: 200px">
            <template #body="{ data }">
              <span v-if="data.note" class="note-text" :title="data.note">
                {{ truncateNote(data.note) }}
              </span>
              <span v-else class="text-muted">-</span>
            </template>
          </Column>

          <template #empty>
            <div class="empty-table">
              <i class="pi pi-inbox"></i>
              <p>Keine Transaktionen gefunden</p>
            </div>
          </template>
        </DataTable>
      </template>
    </Card>

    <!-- Transaction Dialog -->
    <TransactionDialog
      v-model="showTransactionDialog"
      @success="onTransactionSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Dropdown from 'primevue/dropdown'
import DatePicker from 'primevue/datepicker'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Badge from 'primevue/badge'
import TransactionTypeBadge from '../atoms/TransactionTypeBadge.vue'
import TransactionDialog from '../molecules/TransactionDialog.vue'
import { useInventoryStore } from '@/stores/inventory'
import { TRANSACTION_TYPES } from '@/types/inventory'
import type { TransactionType } from '@/types/inventory'

const inventoryStore = useInventoryStore()

const filters = ref({
  search: '',
  type: null as TransactionType | null,
  dateFrom: null as Date | null,
  dateTo: null as Date | null
})

const showTransactionDialog = ref(false)

const transactionTypeOptions = [
  { label: 'Alle Typen', value: null },
  ...TRANSACTION_TYPES.map((t) => ({ label: t.label, value: t.value }))
]

const filteredTransactions = computed(() => {
  return inventoryStore.transactions.filter((tx) => {
    // Filter by search
    if (filters.value.search) {
      const searchLower = filters.value.search.toLowerCase()
      const itemName = tx.item_name.toLowerCase()
      const sourceName = (tx.source_name || '').toLowerCase()
      const targetName = (tx.target_name || '').toLowerCase()
      const note = (tx.note || '').toLowerCase()
      if (!itemName.includes(searchLower) &&
          !sourceName.includes(searchLower) &&
          !targetName.includes(searchLower) &&
          !note.includes(searchLower)) {
        return false
      }
    }

    // Filter by type
    if (filters.value.type !== null && tx.transaction_type !== filters.value.type) {
      return false
    }

    // Filter by date range
    if (filters.value.dateFrom || filters.value.dateTo) {
      const txDate = new Date(tx.date)
      if (filters.value.dateFrom && txDate < filters.value.dateFrom) return false
      if (filters.value.dateTo) {
        const endOfDay = new Date(filters.value.dateTo)
        endOfDay.setHours(23, 59, 59, 999)
        if (txDate > endOfDay) return false
      }
    }

    return true
  })
})

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function truncateNote(note: string, maxLength: number = 30): string {
  if (note.length <= maxLength) return note
  return note.substring(0, maxLength) + '...'
}

function onFilterChange() {
  // Filters are reactive
}

function onTransactionSuccess() {
  showTransactionDialog.value = false
}

onMounted(() => {
  // Load transactions if not already loaded
  if (inventoryStore.transactions.length === 0) {
    inventoryStore.fetchTransactions({ limit: 100 })
  }
})
</script>

<style scoped>
.transactions-history {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-header h3 {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.filter-card {
  background: var(--surface-card);
}

.filter-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 1rem;
}

.table-card {
  background: var(--surface-card);
}

.item-name {
  font-weight: 500;
}

.location-flow {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
}

.source,
.target {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.source {
  color: var(--red-500);
}

.target {
  color: var(--green-500);
}

.flow-arrow {
  color: var(--text-color-secondary);
  font-size: 0.75rem;
}

.user-name {
  font-size: 0.875rem;
}

.note-text {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.text-muted {
  color: var(--text-color-secondary);
}

.empty-table {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2rem;
  color: var(--text-color-secondary);
}

.empty-table i {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

@media (max-width: 768px) {
  .section-header {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }

  .filter-grid {
    grid-template-columns: 1fr;
  }
}
</style>
