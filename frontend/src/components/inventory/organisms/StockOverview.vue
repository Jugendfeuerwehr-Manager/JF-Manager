<template>
  <div class="stock-overview">
    <!-- Filters -->
    <Card class="filter-card">
      <template #content>
        <div class="filter-grid">
          <IconField>
            <InputIcon class="pi pi-search" />
            <InputText v-model="filters.search" placeholder="Artikel suchen..." @input="onFilterChange" />
          </IconField>

          <Dropdown
            v-model="filters.category"
            :options="categoryOptions"
            option-label="label"
            option-value="value"
            placeholder="Kategorie"
            show-clear
            @change="onFilterChange"
          />

          <Dropdown
            v-model="filters.location"
            :options="locationOptions"
            option-label="label"
            option-value="value"
            placeholder="Lagerort"
            show-clear
            @change="onFilterChange"
          />

          <div class="filter-actions">
            <Button
              label="Neue Transaktion"
              icon="pi pi-plus"
              @click="selectedStock = undefined; transactionType = undefined; showTransactionDialog = true"
            />
          </div>
        </div>
      </template>
    </Card>

    <!-- Stock Table -->
    <Card class="table-card">
      <template #content>
        <DataTable
          :value="filteredStocks"
          :loading="inventoryStore.stocksLoading"
          :paginator="filteredStocks.length > 20"
          :rows="20"
          :rows-per-page-options="[10, 20, 50]"
          paginator-template="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
          current-page-report-template="{first} bis {last} von {totalRecords}"
          striped-rows
          removable-sort
          class="stock-table"
        >
          <Column field="item_name" header="Artikel" sortable>
            <template #body="{ data }">
              <div class="item-cell">
                <span class="item-name">{{ data.display_name || 'Unbekannt' }}</span>
                <Tag v-if="data.category_name" :value="data.category_name" severity="secondary" size="small" />
              </div>
            </template>
          </Column>

          <Column field="location_name" header="Lagerort" sortable>
            <template #body="{ data }">
              <div class="location-cell">
                <i :class="isLocationMember(data.location) ? 'pi pi-user' : 'pi pi-box'"></i>
                <span>{{ data.location_name }}</span>
              </div>
            </template>
          </Column>

          <Column field="quantity" header="Bestand" sortable style="width: 120px; text-align: center">
            <template #body="{ data }">
              <StockBadge :quantity="data.quantity" />
            </template>
          </Column>

          <Column header="Aktionen" style="width: 200px">
            <template #body="{ data }">
              <div class="action-buttons">
                <Button
                  v-if="!isLocationMember(data.location)"
                  icon="pi pi-user"
                  size="small"
                  text
                  rounded
                  severity="primary"
                  title="Ausleihen"
                  @click="openLoanDialog(data)"
                  :disabled="data.quantity === 0"
                />
                <Button
                  v-if="isLocationMember(data.location)"
                  icon="pi pi-replay"
                  size="small"
                  text
                  rounded
                  severity="success"
                  title="Rückgabe"
                  @click="openReturnDialog(data)"
                  :disabled="data.quantity === 0"
                />
                <Button
                  icon="pi pi-arrows-h"
                  size="small"
                  text
                  rounded
                  severity="info"
                  title="Umlagern"
                  @click="openMoveDialog(data)"
                  :disabled="data.quantity === 0"
                />
                <Button
                  icon="pi pi-trash"
                  size="small"
                  text
                  rounded
                  severity="danger"
                  title="Aussortieren"
                  @click="openDiscardDialog(data)"
                  :disabled="data.quantity === 0"
                />
              </div>
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

    <!-- Transaction Dialog -->
    <TransactionDialog
      v-model="showTransactionDialog"
      :initial-type="transactionType"
      :initial-stock="selectedStock"
      @success="onTransactionSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Dropdown from 'primevue/dropdown'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import StockBadge from '../atoms/StockBadge.vue'
import TransactionDialog from '../molecules/TransactionDialog.vue'
import { useInventoryStore } from '@/stores/inventory'
import type { Stock, TransactionType } from '@/types/inventory'

const inventoryStore = useInventoryStore()

const filters = ref({
  search: '',
  category: null as number | null,
  location: null as number | null
})

const showTransactionDialog = ref(false)
const transactionType = ref<TransactionType | undefined>(undefined)
const selectedStock = ref<Stock | undefined>(undefined)

const categoryOptions = computed(() => [
  { label: 'Alle Kategorien', value: null },
  ...inventoryStore.categoryOptions
])

const locationOptions = computed(() => [
  { label: 'Alle Lagerorte', value: null },
  ...inventoryStore.locationOptions
])

const filteredStocks = computed(() => {
  return inventoryStore.stocks.filter((stock) => {
    // Filter by search
    if (filters.value.search) {
      const searchLower = filters.value.search.toLowerCase()
      const itemName = (stock.variant_display || stock.item_name || '').toLowerCase()
      const locationName = stock.location_name.toLowerCase()
      if (!itemName.includes(searchLower) && !locationName.includes(searchLower)) {
        return false
      }
    }

    // Filter by category
    if (filters.value.category !== null && stock.category_id !== filters.value.category) {
      return false
    }

    // Filter by location
    if (filters.value.location !== null && stock.location !== filters.value.location) {
      return false
    }

    // Only show stocks with quantity > 0
    if (stock.quantity === 0) {
      return false
    }

    return true
  })
})

function isLocationMember(locationId: number): boolean {
  const location = inventoryStore.locations.find((l) => l.id === locationId)
  return location?.is_member || false
}

function onFilterChange() {
  // Filters are reactive, no need to do anything
}

function openLoanDialog(stock: Stock) {
  selectedStock.value = stock
  transactionType.value = 'LOAN'
  showTransactionDialog.value = true
}

function openReturnDialog(stock: Stock) {
  selectedStock.value = stock
  transactionType.value = 'RETURN'
  showTransactionDialog.value = true
}

function openMoveDialog(stock: Stock) {
  selectedStock.value = stock
  transactionType.value = 'MOVE'
  showTransactionDialog.value = true
}

function openDiscardDialog(stock: Stock) {
  selectedStock.value = stock
  transactionType.value = 'DISCARD'
  showTransactionDialog.value = true
}

function onTransactionSuccess() {
  showTransactionDialog.value = false
  selectedStock.value = undefined
  transactionType.value = undefined
}
</script>

<style scoped>
.stock-overview {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.filter-card {
  background: var(--surface-card);
}

.filter-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr auto;
  gap: 1rem;
  align-items: center;
}

.filter-actions {
  display: flex;
  gap: 0.5rem;
}

.table-card {
  background: var(--surface-card);
}

.stock-table {
  font-size: 0.9rem;
}

.item-cell {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.item-name {
  font-weight: 500;
}

.location-cell {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.action-buttons {
  display: flex;
  gap: 0.25rem;
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
  .filter-grid {
    grid-template-columns: 1fr;
  }

  .filter-actions {
    width: 100%;
  }

  .filter-actions button {
    width: 100%;
  }
}
</style>
