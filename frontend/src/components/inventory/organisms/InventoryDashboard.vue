<template>
  <div class="inventory-dashboard">
    <!-- Stats Row -->
    <div class="stats-grid">
      <Card class="stat-card clickable" @click="$emit('navigate', 'stock')">
        <template #content>
          <div class="stat-content">
            <div class="stat-icon-wrapper blue">
              <i class="pi pi-box"></i>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ totalStock }}</span>
              <span class="stat-label">Artikel im Bestand</span>
            </div>
          </div>
        </template>
      </Card>

      <Card class="stat-card clickable" @click="$emit('navigate', 'loans')">
        <template #content>
          <div class="stat-content">
            <div class="stat-icon-wrapper orange">
              <i class="pi pi-users"></i>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ itemsOnLoan }}</span>
              <span class="stat-label">Ausgeliehene Artikel</span>
            </div>
          </div>
        </template>
      </Card>

      <Card class="stat-card clickable" @click="$emit('navigate', 'items')">
        <template #content>
          <div class="stat-content">
            <div class="stat-icon-wrapper green">
              <i class="pi pi-list"></i>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ totalItems }}</span>
              <span class="stat-label">Artikeltypen</span>
            </div>
          </div>
        </template>
      </Card>

      <Card class="stat-card clickable" @click="$emit('navigate', 'locations')">
        <template #content>
          <div class="stat-content">
            <div class="stat-icon-wrapper purple">
              <i class="pi pi-map-marker"></i>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ totalLocations }}</span>
              <span class="stat-label">Lagerorte</span>
            </div>
          </div>
        </template>
      </Card>
    </div>

    <!-- Quick Actions & Recent Activity -->
    <div class="dashboard-grid">
      <!-- Quick Actions -->
      <Card class="quick-actions-card">
        <template #title>
          <div class="card-title">
            <i class="pi pi-bolt"></i>
            Schnellaktionen
          </div>
        </template>
        <template #content>
          <div class="quick-actions">
            <Button
              label="Artikel ausleihen"
              icon="pi pi-user"
              class="action-button"
              severity="primary"
              @click="showQuickLoanDialog = true"
            />
            <Button
              label="Rückgabe erfassen"
              icon="pi pi-replay"
              class="action-button"
              severity="success"
              @click="showQuickReturnDialog = true"
            />
            <Button
              label="Wareneingang"
              icon="pi pi-arrow-down"
              class="action-button"
              severity="info"
              @click="openTransactionDialog('IN')"
            />
            <Button
              label="Umlagerung"
              icon="pi pi-arrows-h"
              class="action-button"
              severity="secondary"
              @click="openTransactionDialog('MOVE')"
            />
          </div>
        </template>
      </Card>

      <!-- Recent Loans -->
      <Card class="recent-loans-card">
        <template #title>
          <div class="card-title">
            <i class="pi pi-users"></i>
            Aktuelle Ausleihen
          </div>
        </template>
        <template #content>
          <div v-if="recentLoans.length > 0" class="recent-loans">
            <div v-for="loan in recentLoans" :key="loan.member_id" class="loan-item">
              <Avatar :label="getInitials(loan.member_name)" size="normal" shape="circle" />
              <div class="loan-info">
                <span class="loan-member">{{ loan.member_name }}</span>
                <span class="loan-count">{{ loan.total_items }} Artikel</span>
              </div>
            </div>
          </div>
          <div v-else class="empty-state">
            <i class="pi pi-check-circle"></i>
            <p>Keine aktiven Ausleihen</p>
          </div>
          <Button
            v-if="recentLoans.length > 0"
            label="Alle anzeigen"
            text
            size="small"
            class="show-all-button"
            @click="$emit('navigate', 'loans')"
          />
        </template>
      </Card>

      <!-- Low Stock Alert -->
      <Card class="low-stock-card">
        <template #title>
          <div class="card-title">
            <i class="pi pi-exclamation-triangle"></i>
            Niedriger Bestand
          </div>
        </template>
        <template #content>
          <div v-if="lowStockItems.length > 0" class="low-stock-items">
            <div v-for="item in lowStockItems" :key="item.id" class="low-stock-item">
              <span class="item-name">{{ item.variant_display || item.item_name }}</span>
              <Badge :value="item.quantity" severity="warning" />
            </div>
          </div>
          <div v-else class="empty-state success">
            <i class="pi pi-check-circle"></i>
            <p>Alle Bestände in Ordnung</p>
          </div>
        </template>
      </Card>

      <!-- Recent Transactions -->
      <Card class="recent-transactions-card">
        <template #title>
          <div class="card-title">
            <i class="pi pi-history"></i>
            Letzte Transaktionen
          </div>
        </template>
        <template #content>
          <div v-if="recentTransactions.length > 0" class="recent-transactions">
            <div v-for="tx in recentTransactions" :key="tx.id" class="transaction-item">
              <TransactionTypeBadge :type="tx.transaction_type" />
              <div class="transaction-info">
                <span class="transaction-item-name">{{ tx.item_name }}</span>
                <span class="transaction-date">{{ formatDate(tx.date) }}</span>
              </div>
              <Badge :value="tx.quantity" severity="secondary" />
            </div>
          </div>
          <div v-else class="empty-state">
            <i class="pi pi-inbox"></i>
            <p>Keine Transaktionen</p>
          </div>
          <Button
            v-if="recentTransactions.length > 0"
            label="Alle anzeigen"
            text
            size="small"
            class="show-all-button"
            @click="$emit('navigate', 'history')"
          />
        </template>
      </Card>
    </div>

    <!-- Transaction Dialog -->
    <TransactionDialog
      v-model="showTransactionDialog"
      :initial-type="transactionType"
      @success="onTransactionSuccess"
    />

    <!-- Quick Loan Dialog -->
    <QuickLoanDialog
      v-model="showQuickLoanDialog"
      @success="onTransactionSuccess"
    />

    <!-- Quick Return Dialog -->
    <QuickReturnDialog
      v-model="showQuickReturnDialog"
      @success="onTransactionSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Avatar from 'primevue/avatar'
import Badge from 'primevue/badge'
import TransactionTypeBadge from '../atoms/TransactionTypeBadge.vue'
import TransactionDialog from '../molecules/TransactionDialog.vue'
import QuickLoanDialog from '../molecules/QuickLoanDialogV2.vue'
import QuickReturnDialog from '../molecules/QuickReturnDialog.vue'
import { useInventoryStore } from '@/stores/inventory'
import type { TransactionType } from '@/types/inventory'

defineEmits<{
  navigate: [tab: string]
}>()

const inventoryStore = useInventoryStore()

const showTransactionDialog = ref(false)
const showQuickLoanDialog = ref(false)
const showQuickReturnDialog = ref(false)
const transactionType = ref<TransactionType>('LOAN')

// Computed stats
const totalStock = computed(() => {
  return inventoryStore.stocks.reduce((sum, s) => sum + s.quantity, 0)
})

const itemsOnLoan = computed(() => {
  return inventoryStore.memberLoans.reduce((sum, loan) => sum + loan.total_items, 0)
})

const totalItems = computed(() => inventoryStore.items.length)
const totalLocations = computed(() => inventoryStore.locations.length)

const recentLoans = computed(() => {
  return inventoryStore.memberLoans.slice(0, 5)
})

const lowStockItems = computed(() => {
  return inventoryStore.stocks
    .filter((s) => {
      const location = inventoryStore.locations.find((l) => l.id === s.location)
      return !location?.is_member && s.quantity > 0 && s.quantity <= 5
    })
    .slice(0, 5)
})

const recentTransactions = computed(() => {
  return inventoryStore.transactions.slice(0, 5)
})

function getInitials(name: string): string {
  const parts = name.split(' ')
  const first = parts[0]
  const last = parts[parts.length - 1]
  if (parts.length >= 2 && first && last && first.length > 0 && last.length > 0) {
    return (first.charAt(0) + last.charAt(0)).toUpperCase()
  }
  return name.substring(0, 2).toUpperCase()
}

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function openTransactionDialog(type: TransactionType) {
  transactionType.value = type
  showTransactionDialog.value = true
}

function onTransactionSuccess() {
  showTransactionDialog.value = false
  showQuickLoanDialog.value = false
  showQuickReturnDialog.value = false
}
</script>

<style scoped>
.inventory-dashboard {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}

.stat-card {
  cursor: pointer;
  transition: all 0.2s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.stat-icon-wrapper {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
}

.stat-icon-wrapper.blue {
  background: rgba(59, 130, 246, 0.1);
  color: rgb(59, 130, 246);
}

.stat-icon-wrapper.orange {
  background: rgba(249, 115, 22, 0.1);
  color: rgb(249, 115, 22);
}

.stat-icon-wrapper.green {
  background: rgba(34, 197, 94, 0.1);
  color: rgb(34, 197, 94);
}

.stat-icon-wrapper.purple {
  background: rgba(168, 85, 247, 0.1);
  color: rgb(168, 85, 247);
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-color);
  line-height: 1;
}

.stat-label {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
  margin-top: 0.25rem;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
}

.action-button {
  width: 100%;
  justify-content: flex-start;
}

.recent-loans,
.low-stock-items,
.recent-transactions {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.loan-item,
.low-stock-item,
.transaction-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem;
  background: var(--surface-ground);
  border-radius: var(--border-radius);
}

.loan-info,
.transaction-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.loan-member,
.transaction-item-name,
.item-name {
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.loan-count,
.transaction-date {
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1.5rem;
  color: var(--text-color-secondary);
}

.empty-state i {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.empty-state.success {
  color: var(--green-500);
}

.show-all-button {
  margin-top: 0.5rem;
  width: 100%;
}

@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .dashboard-grid {
    grid-template-columns: 1fr;
  }

  .quick-actions {
    grid-template-columns: 1fr;
  }
}
</style>
