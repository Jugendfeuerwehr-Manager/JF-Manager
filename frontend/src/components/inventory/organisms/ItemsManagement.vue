<template>
  <div class="items-management">
    <!-- Header -->
    <div class="section-header">
      <h3>
        <i class="pi pi-box"></i>
        Artikel verwalten
      </h3>
      <Button label="Neuer Artikel" icon="pi pi-plus" @click="openCreateDialog" />
    </div>

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
        </div>
      </template>
    </Card>

    <!-- Items Table -->
    <Card class="table-card">
      <template #content>
        <DataTable
          :value="filteredItems"
          :loading="inventoryStore.itemsLoading"
          :paginator="filteredItems.length > 10"
          :rows="10"
          :rows-per-page-options="[10, 20, 50]"
          paginator-template="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
          current-page-report-template="{first} bis {last} von {totalRecords}"
          striped-rows
          removable-sort
          @row-click="onRowClick"
          class="clickable-rows"
        >
          <Column field="name" header="Name" sortable>
            <template #body="{ data }">
              <div class="item-cell">
                <div class="item-name-row">
                  <span class="item-name">{{ data.name }}</span>
                  <Tag v-if="data.department === null" value="G" icon="pi pi-globe" severity="contrast" />
                </div>
                <span v-if="data.is_variant_parent" class="variant-info">
                  <i class="pi pi-sitemap"></i>
                  {{ data.variants?.length || 0 }} Varianten
                </span>
              </div>
            </template>
          </Column>

          <Column field="category_name" header="Kategorie" sortable>
            <template #body="{ data }">
              <Tag v-if="data.category_name" :value="data.category_name" severity="secondary" />
              <span v-else class="text-muted">-</span>
            </template>
          </Column>

          <Column field="base_unit" header="Einheit" sortable style="width: 120px" />

          <Column field="total_stock" header="Bestand" sortable style="width: 120px; text-align: center">
            <template #body="{ data }">
              <StockBadge :quantity="data.total_stock" />
            </template>
          </Column>

          <Column header="Aktionen" style="width: 150px">
            <template #body="{ data }">
              <div class="action-buttons">
                <Button
                  icon="pi pi-pencil"
                  size="small"
                  text
                  rounded
                  severity="secondary"
                  title="Bearbeiten"
                  @click.stop="openEditDialog(data)"
                />
                <Button
                  icon="pi pi-trash"
                  size="small"
                  text
                  rounded
                  severity="danger"
                  title="Löschen"
                  @click.stop="confirmDelete(data)"
                />
              </div>
            </template>
          </Column>

          <template #empty>
            <div class="empty-table">
              <i class="pi pi-inbox"></i>
              <p>Keine Artikel gefunden</p>
              <Button label="Artikel erstellen" icon="pi pi-plus" @click="openCreateDialog" />
            </div>
          </template>
        </DataTable>
      </template>
    </Card>

    <!-- Item Form Dialog -->
    <ItemFormDialog
      v-model="showItemDialog"
      :item="selectedItem"
      @success="onItemSaved"
    />

    <!-- Delete Confirmation -->
    <ConfirmDialog />
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
import ConfirmDialog from 'primevue/confirmdialog'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import StockBadge from '../atoms/StockBadge.vue'
import ItemFormDialog from '../molecules/ItemFormDialog.vue'
import { useInventoryStore } from '@/stores/inventory'
import type { Item } from '@/types/inventory'

const inventoryStore = useInventoryStore()
const confirm = useConfirm()
const toast = useToast()

const filters = ref({
  search: '',
  category: null as number | null
})

const showItemDialog = ref(false)
const selectedItem = ref<Item | null>(null)

const categoryOptions = computed(() => [
  { label: 'Alle Kategorien', value: null },
  ...inventoryStore.categoryOptions
])

const filteredItems = computed(() => {
  return inventoryStore.items.filter((item) => {
    // Filter by search
    if (filters.value.search) {
      const searchLower = filters.value.search.toLowerCase()
      const name = item.name.toLowerCase()
      const categoryName = (item.category_name || '').toLowerCase()
      if (!name.includes(searchLower) && !categoryName.includes(searchLower)) {
        return false
      }
    }

    // Filter by category
    if (filters.value.category !== null && item.category !== filters.value.category) {
      return false
    }

    return true
  })
})

function onFilterChange() {
  // Filters are reactive
}

function onRowClick(event: { data: Item }) {
  openEditDialog(event.data)
}

function openCreateDialog() {
  selectedItem.value = null
  showItemDialog.value = true
}

function openEditDialog(item: Item) {
  selectedItem.value = item
  showItemDialog.value = true
}

function confirmDelete(item: Item) {
  confirm.require({
    message: `Möchten Sie den Artikel "${item.name}" wirklich löschen?`,
    header: 'Artikel löschen',
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    acceptLabel: 'Löschen',
    rejectLabel: 'Abbrechen',
    accept: async () => {
      try {
        await inventoryStore.deleteItem(item.id)
        toast.add({
          severity: 'success',
          summary: 'Erfolg',
          detail: 'Artikel wurde gelöscht',
          life: 3000
        })
      } catch {
        toast.add({
          severity: 'error',
          summary: 'Fehler',
          detail: 'Artikel konnte nicht gelöscht werden',
          life: 5000
        })
      }
    }
  })
}

function onItemSaved() {
  showItemDialog.value = false
  selectedItem.value = null
}
</script>

<style scoped>
.items-management {
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
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.table-card {
  background: var(--surface-card);
}

.clickable-rows :deep(tr) {
  cursor: pointer;
}

.item-cell {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.item-name {
  font-weight: 500;
}

.item-name-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.variant-info {
  font-size: 0.8rem;
  color: var(--text-color-secondary);
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.text-muted {
  color: var(--text-color-secondary);
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
