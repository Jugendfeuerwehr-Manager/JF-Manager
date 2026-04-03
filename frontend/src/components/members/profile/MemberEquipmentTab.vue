<template>
  <div class="member-equipment-tab">
    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <ProgressSpinner />
    </div>

    <!-- Content -->
    <div v-else>
      <!-- Header Actions -->
      <div class="equipment-header">
        <div class="equipment-stats">
          <Tag severity="info" :value="`${totalItems} Artikel ausgeliehen`" icon="pi pi-box" />
        </div>
        <div class="equipment-actions">
          <Button
            label="Ausleihen"
            icon="pi pi-arrow-right"
            severity="primary"
            @click="showLoanDialog = true"
          />
          <Button
            label="Rückgabe"
            icon="pi pi-arrow-left"
            severity="secondary"
            :disabled="equipment.length === 0"
            @click="showReturnDialog = true"
          />
          <Button
            label="Aussortieren"
            icon="pi pi-trash"
            severity="danger"
            outlined
            :disabled="equipment.length === 0"
            @click="initiateDiscard(null)"
          />
        </div>
      </div>

      <!-- Equipment List -->
      <Card v-if="equipment.length > 0" class="equipment-card">
        <template #title>
          <div class="card-title">
            <i class="pi pi-box"></i>
            <span>Ausgeliehene Ausrüstung</span>
          </div>
        </template>
        <template #content>
          <DataTable :value="equipment" responsiveLayout="scroll" stripedRows>
            <Column field="display_name" header="Artikel">
              <template #body="{ data }">
                <div class="item-cell">
                  <span class="item-name">{{ data.display_name }}</span>
                  <Tag
                    v-if="data.category_name"
                    :value="data.category_name"
                    severity="secondary"
                    class="category-tag"
                  />
                </div>
              </template>
            </Column>
            <Column field="quantity" header="Anzahl" style="width: 100px">
              <template #body="{ data }">
                <Tag :value="data.quantity.toString()" severity="info" />
              </template>
            </Column>
            <Column header="Aktionen" style="width: 120px">
              <template #body="{ data }">
                <Button
                  icon="pi pi-undo"
                  severity="secondary"
                  text
                  rounded
                  v-tooltip.top="'Zurückgeben'"
                  @click="initiateReturn(data)"
                />
                <Button
                  icon="pi pi-trash"
                  severity="danger"
                  text
                  rounded
                  v-tooltip.top="'Aussortieren (verloren/defekt)'"
                  @click="initiateDiscard(data)"
                />
              </template>
            </Column>
          </DataTable>
        </template>
      </Card>

      <!-- Empty State -->
      <Card v-else class="empty-card">
        <template #content>
          <div class="empty-state">
            <i class="pi pi-inbox"></i>
            <p>Keine Ausrüstung ausgeliehen</p>
            <small>Klicken Sie auf "Ausleihen", um diesem Mitglied Ausrüstung zuzuweisen.</small>
          </div>
        </template>
      </Card>

      <!-- Recent Transactions -->
      <Card v-if="recentTransactions.length > 0" class="transactions-card">
        <template #title>
          <div class="card-title">
            <i class="pi pi-history"></i>
            <span>Letzte Transaktionen</span>
          </div>
        </template>
        <template #content>
          <DataTable :value="recentTransactions" responsiveLayout="scroll">
            <Column field="date" header="Datum" style="width: 120px">
              <template #body="{ data }">
                {{ formatDate(data.date) }}
              </template>
            </Column>
            <Column field="transaction_type" header="Typ" style="width: 100px">
              <template #body="{ data }">
                <Tag
                  :value="getTransactionTypeLabel(data.transaction_type)"
                  :severity="getTransactionTypeSeverity(data.transaction_type)"
                />
              </template>
            </Column>
            <Column field="item_name" header="Artikel">
              <template #body="{ data }">
                {{ data.item_name }}
              </template>
            </Column>
            <Column field="quantity" header="Menge" style="width: 80px" />
          </DataTable>
        </template>
      </Card>
    </div>

    <!-- Loan Dialog -->
    <QuickLoanDialog
      v-model="showLoanDialog"
      :preselected-member="memberLocationId || undefined"
      @success="onTransactionSuccess"
    />

    <!-- Return Dialog -->
    <QuickReturnDialog
      v-model="showReturnDialog"
      :preselected-member="memberLocationId || undefined"
      @success="onTransactionSuccess"
    />

    <!-- Discard Dialog -->
    <TransactionDialog
      v-model="showDiscardDialog"
      initial-type="DISCARD"
      :initial-stock="selectedDiscardStock || undefined"
      @success="onTransactionSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import { locationsApi } from '@/api/inventory'
import { useInventoryStore } from '@/stores/inventory'
import type { Stock, Transaction, MemberEquipmentResponse } from '@/types/inventory'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ProgressSpinner from 'primevue/progressspinner'
import QuickLoanDialog from '@/components/inventory/molecules/QuickLoanDialogV2.vue'
import QuickReturnDialog from '@/components/inventory/molecules/QuickReturnDialog.vue'
import TransactionDialog from '@/components/inventory/molecules/TransactionDialog.vue'

interface Props {
  memberId: number
}

const props = defineProps<Props>()
const toast = useToast()
const inventoryStore = useInventoryStore()

// State
const loading = ref(true)
const equipment = ref<Stock[]>([])
const recentTransactions = ref<Transaction[]>([])
const memberLocationId = ref<number | null>(null)
const showLoanDialog = ref(false)
const showReturnDialog = ref(false)
const showDiscardDialog = ref(false)
const selectedDiscardStock = ref<Stock | null>(null)

// Computed
const totalItems = computed(() => equipment.value.reduce((sum, e) => sum + e.quantity, 0))

// Methods
const loadEquipment = async () => {
  loading.value = true
  try {
    // Load locations and items for the dialogs
    await Promise.all([
      inventoryStore.fetchLocations({ limit: 1000 }),
      inventoryStore.fetchItems({ limit: 1000 }),
      inventoryStore.fetchVariants({ limit: 1000 }),
      inventoryStore.fetchStocks({ limit: 1000 })
    ])

    // Get member equipment
    const response = await locationsApi.getMemberEquipment(props.memberId)
    equipment.value = response.data.equipment
    recentTransactions.value = response.data.recent_transactions
    memberLocationId.value = response.data.location_id
  } catch (error) {
    console.error('Error loading equipment:', error)
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Ausrüstung konnte nicht geladen werden',
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

const initiateReturn = (stock: Stock) => {
  // Pre-select the item in the return dialog
  showReturnDialog.value = true
}

const initiateDiscard = (stock: Stock | null) => {
  selectedDiscardStock.value = stock
  showDiscardDialog.value = true
}

const onTransactionSuccess = async () => {
  showLoanDialog.value = false
  showReturnDialog.value = false
  showDiscardDialog.value = false
  selectedDiscardStock.value = null
  await loadEquipment()
  toast.add({
    severity: 'success',
    summary: 'Erfolg',
    detail: 'Transaktion erfolgreich',
    life: 3000
  })
}

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString('de-DE', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

const getTransactionTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    IN: 'Eingang',
    OUT: 'Ausgang',
    LOAN: 'Ausleihe',
    RETURN: 'Rückgabe',
    MOVE: 'Umzug',
    DISCARD: 'Ausschuss'
  }
  return labels[type] || type
}

const getTransactionTypeSeverity = (type: string) => {
  const severities: Record<string, 'success' | 'info' | 'warn' | 'danger' | 'secondary'> = {
    IN: 'success',
    OUT: 'danger',
    LOAN: 'warn',
    RETURN: 'success',
    MOVE: 'info',
    DISCARD: 'danger'
  }
  return severities[type] || 'secondary'
}

onMounted(() => {
  loadEquipment()
})
</script>

<style scoped>
.member-equipment-tab {
  padding: 1rem 0;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}

.equipment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.equipment-stats {
  display: flex;
  gap: 0.5rem;
}

.equipment-actions {
  display: flex;
  gap: 0.5rem;
}

.equipment-card,
.transactions-card,
.empty-card {
  margin-bottom: 1.5rem;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.1rem;
  font-weight: 600;
}

.card-title i {
  color: var(--primary-color);
}

.item-cell {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.item-name {
  font-weight: 500;
}

.category-tag {
  width: fit-content;
  font-size: 0.75rem;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  text-align: center;
  gap: 1rem;
}

.empty-state i {
  font-size: 3rem;
  color: var(--text-color-secondary);
}

.empty-state p {
  margin: 0;
  color: var(--text-color-secondary);
  font-size: 1.1rem;
}

.empty-state small {
  color: var(--text-color-secondary);
}

@media (max-width: 768px) {
  .equipment-header {
    flex-direction: column;
    align-items: stretch;
  }

  .equipment-actions {
    flex-direction: column;
  }

  .equipment-actions :deep(.p-button) {
    width: 100%;
  }
}
</style>
